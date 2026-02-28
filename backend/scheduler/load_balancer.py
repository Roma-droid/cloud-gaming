"""Load balancer: distributes game instances across server nodes based on resource availability."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

from backend.utils.redis import get_redis

logger = structlog.get_logger(__name__)


@dataclass
class NodeStatus:
    """Represents a server node's resource status."""

    node_id: str
    hostname: str
    cpu_total: float  # Number of cores
    cpu_used: float
    memory_total_mb: float
    memory_used_mb: float
    gpu_count: int = 0
    gpu_used: int = 0
    active_instances: int = 0
    max_instances: int = 10
    is_healthy: bool = True
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def cpu_available(self) -> float:
        return max(0, self.cpu_total - self.cpu_used)

    @property
    def memory_available_mb(self) -> float:
        return max(0, self.memory_total_mb - self.memory_used_mb)

    @property
    def gpu_available(self) -> int:
        return max(0, self.gpu_count - self.gpu_used)

    @property
    def load_score(self) -> float:
        """Lower score = less loaded = preferred for new instances."""
        if not self.is_healthy or self.active_instances >= self.max_instances:
            return float("inf")
        cpu_ratio = self.cpu_used / self.cpu_total if self.cpu_total else 1.0
        mem_ratio = self.memory_used_mb / self.memory_total_mb if self.memory_total_mb else 1.0
        instance_ratio = self.active_instances / self.max_instances
        return (cpu_ratio * 0.4) + (mem_ratio * 0.3) + (instance_ratio * 0.3)


class LoadBalancer:
    """Distributes game instances across available server nodes."""

    REDIS_PREFIX = "lb:node:"
    HEARTBEAT_TTL = 30  # seconds

    async def register_node(self, node: NodeStatus) -> None:
        """Register or update a server node."""
        redis = await get_redis()
        key = f"{self.REDIS_PREFIX}{node.node_id}"
        await redis.hset(key, mapping={
            "hostname": node.hostname,
            "cpu_total": str(node.cpu_total),
            "cpu_used": str(node.cpu_used),
            "memory_total_mb": str(node.memory_total_mb),
            "memory_used_mb": str(node.memory_used_mb),
            "gpu_count": str(node.gpu_count),
            "gpu_used": str(node.gpu_used),
            "active_instances": str(node.active_instances),
            "max_instances": str(node.max_instances),
            "is_healthy": "1" if node.is_healthy else "0",
            "last_heartbeat": node.last_heartbeat.isoformat(),
        })
        await redis.expire(key, self.HEARTBEAT_TTL)
        logger.debug("node_registered", node_id=node.node_id, load=node.load_score)

    async def get_all_nodes(self) -> list[NodeStatus]:
        """Get all registered and healthy nodes."""
        redis = await get_redis()
        nodes: list[NodeStatus] = []

        # Scan for node keys
        async for key in redis.scan_iter(f"{self.REDIS_PREFIX}*"):
            data = await redis.hgetall(key)
            if not data:
                continue

            node_id = key.removeprefix(self.REDIS_PREFIX) if isinstance(key, str) else key.decode().removeprefix(self.REDIS_PREFIX)
            try:
                node = NodeStatus(
                    node_id=node_id,
                    hostname=data.get("hostname", ""),
                    cpu_total=float(data.get("cpu_total", 0)),
                    cpu_used=float(data.get("cpu_used", 0)),
                    memory_total_mb=float(data.get("memory_total_mb", 0)),
                    memory_used_mb=float(data.get("memory_used_mb", 0)),
                    gpu_count=int(data.get("gpu_count", 0)),
                    gpu_used=int(data.get("gpu_used", 0)),
                    active_instances=int(data.get("active_instances", 0)),
                    max_instances=int(data.get("max_instances", 10)),
                    is_healthy=data.get("is_healthy") == "1",
                )
                nodes.append(node)
            except (ValueError, TypeError) as e:
                logger.warning("invalid_node_data", node_id=node_id, error=str(e))

        return nodes

    async def select_node(
        self,
        required_cpu: float = 2.0,
        required_memory_mb: float = 2048,
        require_gpu: bool = False,
    ) -> NodeStatus | None:
        """Select the best available node for a new game instance."""
        nodes = await self.get_all_nodes()

        candidates = [
            n for n in nodes
            if n.is_healthy
            and n.active_instances < n.max_instances
            and n.cpu_available >= required_cpu
            and n.memory_available_mb >= required_memory_mb
            and (not require_gpu or n.gpu_available > 0)
        ]

        if not candidates:
            logger.warning(
                "no_available_nodes",
                total_nodes=len(nodes),
                required_cpu=required_cpu,
                required_memory=required_memory_mb,
                require_gpu=require_gpu,
            )
            return None

        # Sort by load score (least loaded first)
        candidates.sort(key=lambda n: n.load_score)
        selected = candidates[0]

        logger.info("node_selected", node_id=selected.node_id, load=selected.load_score)
        return selected

    async def update_node_usage(
        self,
        node_id: str,
        cpu_delta: float = 0,
        memory_delta_mb: float = 0,
        gpu_delta: int = 0,
        instance_delta: int = 0,
    ) -> None:
        """Update a node's resource usage."""
        redis = await get_redis()
        key = f"{self.REDIS_PREFIX}{node_id}"

        if not await redis.exists(key):
            return

        pipe = redis.pipeline()
        if cpu_delta:
            pipe.hincrbyfloat(key, "cpu_used", cpu_delta)
        if memory_delta_mb:
            pipe.hincrbyfloat(key, "memory_used_mb", memory_delta_mb)
        if gpu_delta:
            pipe.hincrby(key, "gpu_used", gpu_delta)
        if instance_delta:
            pipe.hincrby(key, "active_instances", instance_delta)
        await pipe.execute()

    async def remove_node(self, node_id: str) -> None:
        """Unregister a node."""
        redis = await get_redis()
        await redis.delete(f"{self.REDIS_PREFIX}{node_id}")
        logger.info("node_removed", node_id=node_id)


# Singleton
load_balancer = LoadBalancer()
