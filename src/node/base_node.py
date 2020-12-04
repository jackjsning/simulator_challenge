"""Provides a base class for all IPC nodes in our system.

Generally BaseNode should be subclassed by business logic in other node modules.
"""

import asyncio
import concurrent.futures
import os
import sys
from typing import Callable, Dict, List

from ipc import core, pubsub, rpc


class BaseNode:
    """Base class for all our nodes.

    Primarily designed to make IPC simpler for business logic. Goal is for subclass
    nodes to only worry about the topic and RPC specs and not bother with implementing
    the underlying IPC objects.

    Also provides support for running background tasks for, e.g., reading from hardware
    in a loop.
    """

    def __init__(self, node_id: core.NodeID):
        self._node_id = node_id

        self._publishers: Dict[core.TopicSpec, pubsub.Publisher] = {}
        self._subscribers: List[pubsub.Subscriber] = []

        self._rpc_clients: Dict[core.RPCSpec, rpc.RPCClient] = {}
        self._rpc_servers: List[rpc.RPCServer] = []

        self._task_funcs: List[Callable] = []
        self._running_tasks: List[asyncio.Task] = []

        # Executor supports running non asyncio-compatible loops, as well
        self._executor = concurrent.futures.ThreadPoolExecutor()

    def add_publishers(self, *topic_specs: core.TopicSpec) -> None:
        for topic_spec in topic_specs:
            self._publishers[topic_spec] = pubsub.Publisher(self._node_id, topic_spec)

    def publish(self, topic_spec: core.TopicSpec, msg: core.Message) -> None:
        self._publishers[topic_spec].publish(msg)

    def add_subscribers(self, topic_callbacks: Dict[core.TopicSpec, Callable]) -> None:
        for topic_spec, callback in topic_callbacks.items():
            self._subscribers.append(
                pubsub.Subscriber(self._node_id, topic_spec, callback)
            )

    def add_rpc_clients(self, *rpc_specs: core.RPCSpec) -> None:
        for rpc_spec in rpc_specs:
            self._rpc_clients[rpc_spec] = rpc.RPCClient(self._node_id, rpc_spec)

    async def rpc_call(
        self,
        rpc_spec: core.RPCSpec,
        request_msg: core.RPCRequest,
    ) -> core.RPCResponse:
        return await self._rpc_clients[rpc_spec].call(request_msg)

    def cancel_running_procedure(self, rpc_spec: core.RPCSpec) -> None:
        self._rpc_clients[rpc_spec].cancel_running_procedure()

    def add_rpc_servers(self, rpc_proc_funcs: Dict[core.RPCSpec, Callable]) -> None:
        for rpc_spec, proc_func in rpc_proc_funcs.items():
            self._rpc_servers.append(rpc.RPCServer(self._node_id, rpc_spec, proc_func))

    def add_tasks(self, *funcs: Callable) -> None:
        self._task_funcs.extend(funcs)

    def _create_tasks(self) -> None:
        """Creates (and therefore begins running) all the tasks necessary to allow this
        node to receive communications from other nodes.
        """

        self._running_tasks = [
            asyncio.create_task(sub.listen()) for sub in self._subscribers
        ]
        self._running_tasks.extend(
            [asyncio.create_task(server.serve()) for server in self._rpc_servers]
        )

        loop = asyncio.get_running_loop()
        for func in self._task_funcs:
            if asyncio.iscoroutinefunction(func):
                self._running_tasks.append(asyncio.create_task(func()))
            else:
                loop.run_in_executor(self._executor, func)

    async def _run_coro(self) -> None:
        # Cascading excepts to handle asyncio-related gtochas.
        try:
            self._create_tasks()
            await asyncio.gather(*self._running_tasks)
        except asyncio.CancelledError:
            # Raised normally on stops() and signals, so no cause for concern
            pass
        except KeyboardInterrupt:
            # Somtimes hits the internal tasks, depending on exact loop timing
            pass
        except BlockingIOError:
            # Occasionally triggerd by Redis on keyboard interrupt
            pass
        finally:
            # Stop the node if any exceptions at all arise
            self.stop()

    def run(self) -> None:
        """Turns on this node, allowing it to receive IPC input and run background
        tasks.

        Wrapper using asyncio.run() so that this needn't be called in a context where
        an IO loop is already present.
        """

        try:
            asyncio.run(self._run_coro())
        except KeyboardInterrupt:
            # Clean up the terminal nicely
            print()

    def stop(self) -> None:
        for sub in self._subscribers:
            sub.close()
        for task in self._running_tasks:
            task.cancel()
        self._executor.shutdown(wait=False)
