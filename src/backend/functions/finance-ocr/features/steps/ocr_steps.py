from behave import then, use_step_matcher, when

from src.main import _classify, _extract_amount, _extract_date

use_step_matcher("re")


@when(r'I classify the text "([^"]+)"')
def step_classify(context, text):
    context.tx_type, context.category = _classify(text)


@when(r'I extract the amount from "([^"]+)"')
def step_extract_amount(context, text):
    context.amount = _extract_amount(text)


@when(r'I extract the date from "([^"]+)"')
def step_extract_date(context, text):
    context.date = _extract_date(text)


@then(r'the type is "([^"]+)" and category is "([^"]+)"')
def step_type_and_category(context, tx_type, category):
    assert context.tx_type == tx_type, f"Expected type '{tx_type}', got '{context.tx_type}'"
    assert context.category == category, f"Expected category '{category}', got '{context.category}'"


@then(r'the amount is "([^"]+)"')
def step_amount(context, expected):
    assert context.amount is not None, "Expected an amount but got None"
    assert abs(context.amount - float(expected)) < 0.001, \
        f"Expected amount {expected}, got {context.amount}"


@then(r'no amount is extracted')
def step_no_amount(context):
    assert context.amount is None, f"Expected None but got {context.amount}"


@then(r'the date is "([^"]+)"')
def step_date(context, expected):
    assert context.date == expected, f"Expected date '{expected}', got '{context.date}'"


@then(r'no date is extracted')
def step_no_date(context):
    assert context.date is None, f"Expected None but got {context.date}"
