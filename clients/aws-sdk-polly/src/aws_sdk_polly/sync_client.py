# Prototype sync client for Polly - Option C (dedicated sync implementation)

from copy import deepcopy
import logging

from smithy_core.sync.client import ClientCall, RequestPipeline
from smithy_core.sync.retries import RetryStrategyResolver
from smithy_core.exceptions import ExpectationNotMetError
from smithy_core.interceptors import InterceptorChain
from smithy_core.types import TypedProperties
from smithy_http.plugins import user_agent_plugin

from .config import Config, Plugin
from .models import (
    DESCRIBE_VOICES,
    DescribeVoicesInput,
    DescribeVoicesOutput,
)
from .user_agent import aws_user_agent_plugin


logger = logging.getLogger(__name__)


class PollySyncClient:
    """Synchronous Amazon Polly client (prototype).

    Amazon Polly is a web service that makes it easy to synthesize speech
    from text. This is a sync-only prototype with just describe_voices.
    """

    def __init__(
        self, config: Config | None = None, plugins: list[Plugin] | None = None
    ):
        """
        Constructor for `PollySyncClient`.

        Args:
            config:
                Optional configuration for the client. Here you can set things like
                the endpoint for HTTP services or auth credentials.
            plugins:
                A list of callables that modify the configuration dynamically. These
                can be used to set defaults, for example.
        """
        self._config = config or Config()

        client_plugins: list[Plugin] = [aws_user_agent_plugin, user_agent_plugin]
        if plugins:
            client_plugins.extend(plugins)

        for plugin in client_plugins:
            plugin(self._config)

        self._retry_strategy_resolver = RetryStrategyResolver()

    def describe_voices(
        self, input: DescribeVoicesInput, plugins: list[Plugin] | None = None
    ) -> DescribeVoicesOutput:
        """
        Returns the list of voices that are available for use when requesting
        speech synthesis. Each voice speaks a specified language, is either male
        or female, and is identified by an ID, which is the ASCII version of the
        voice name.

        Args:
            input:
                An instance of `DescribeVoicesInput`.
            plugins:
                A list of callables that modify the configuration dynamically.
                Changes made by these plugins only apply for the duration of the
                operation execution and will not affect any other operation
                invocations.

        Returns:
            An instance of `DescribeVoicesOutput`.
        """
        operation_plugins: list[Plugin] = []
        if plugins:
            operation_plugins.extend(plugins)
        config = deepcopy(self._config)
        for plugin in operation_plugins:
            plugin(config)
        if config.protocol is None or config.transport is None:
            raise ExpectationNotMetError(
                "protocol and transport MUST be set on the config to make calls."
            )

        retry_strategy = self._retry_strategy_resolver.resolve_retry_strategy(
            retry_strategy=config.retry_strategy
        )

        pipeline = RequestPipeline(protocol=config.protocol, transport=config.transport)
        call = ClientCall(
            input=input,
            operation=DESCRIBE_VOICES,
            context=TypedProperties({"config": config}),
            interceptor=InterceptorChain(config.interceptors),
            auth_scheme_resolver=config.auth_scheme_resolver,
            supported_auth_schemes=config.auth_schemes,
            endpoint_resolver=config.endpoint_resolver,
            retry_strategy=retry_strategy,
        )

        return pipeline(call)
