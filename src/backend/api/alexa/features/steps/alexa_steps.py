from __future__ import annotations
import asyncio
from typing import Optional

from behave import given, then, use_step_matcher, when

from src.application.send_command import SendCommandHandler
from src.domain.command import AlexaCommand
from src.domain.port import AlexaClientPort

use_step_matcher("re")


class InMemoryAlexaClient(AlexaClientPort):
    def __init__(self, device_name: str) -> None:
        self.device_name = device_name
        self.commands_sent: list[AlexaCommand] = []

    async def send_command(self, command: AlexaCommand) -> None:
        self.commands_sent.append(command)

    async def get_device_names(self) -> list[str]:
        return [self.device_name]


@given('an Alexa client with device "([^"]*)"')
def step_given_client(context, device):
    context.client = InMemoryAlexaClient(device_name=device)
    context.handler = SendCommandHandler(context.client)
    context.last_result = None
    context.last_error = None


@when('I send the command "([^"]*)"')
def step_send_command(context, text):
    context.last_result = asyncio.run(
        context.handler.handle(text, context.client.device_name)
    )


@when('I try to send the command "([^"]*)"')
def step_try_send_command(context, text):
    try:
        asyncio.run(context.handler.handle(text, context.client.device_name))
    except ValueError as e:
        context.last_error = e


@then('the command is dispatched to "([^"]*)"')
def step_dispatched(context, device):
    assert len(context.client.commands_sent) == 1
    assert context.client.commands_sent[0].text != ""


@then('the result has sent equal to true')
def step_result_sent(context):
    assert context.last_result is not None
    assert context.last_result["sent"] is True


@then('I get a ValueError "([^"]*)"')
def step_value_error(context, message):
    assert context.last_error is not None, "Expected a ValueError but none was raised"
    assert message in str(context.last_error)
