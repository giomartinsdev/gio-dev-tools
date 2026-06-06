from behave import then, use_step_matcher, when

from src.application.send_message_use_case import SendMessageUseCase

use_step_matcher("re")


class FakeEvolutionClient:
    def __init__(self):
        self.calls: list[dict] = []

    def send_text(self, message) -> dict:
        self.calls.append({"number": message.number, "text": message.text})
        return {"status": "sent", "number": message.number}


def _setup(context):
    context.client = FakeEvolutionClient()
    context.use_case = SendMessageUseCase(context.client)
    context.last_response = None
    context.last_error = None


# When

@when(r'I send message "([^"]*)" to number "([^"]*)"')
def step_send(context, text, number):
    _setup(context)
    context.last_response = context.use_case.execute(number=number, text=text)
    context.last_error = None


@when(r'I try to send message "([^"]*)" to number "([^"]*)"')
def step_try_send(context, text, number):
    _setup(context)
    try:
        context.use_case.execute(number=number, text=text)
        context.last_error = None
    except Exception as e:
        context.last_error = e


# Then

@then(r'the API is called with number "([^"]+)" and text "([^"]+)"')
def step_api_called(context, number, text):
    assert context.client.calls, "Expected API to be called, but it was not"
    call = context.client.calls[-1]
    assert call["number"] == number, f"Expected number '{number}', got '{call['number']}'"
    assert call["text"] == text, f"Expected text '{text}', got '{call['text']}'"


@then(r'the response is returned')
def step_response_returned(context):
    assert context.last_response is not None, "Expected a response but got None"


@then(r'a validation error contains "([^"]+)"')
def step_validation_error(context, message):
    assert context.last_error is not None, "Expected a validation error but none was raised"
    assert message in str(context.last_error), f"Expected '{message}' in error: {context.last_error}"
