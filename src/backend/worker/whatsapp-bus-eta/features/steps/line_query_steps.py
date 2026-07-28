from behave import then, use_step_matcher, when

from src.domain.line_query import parse_line_query

use_step_matcher("re")


@when(r'I parse the text "([^"]*)"')
def step_parse(context, text):
    context.parsed = parse_line_query(text)


@then(r'the parsed mode is "([^"]+)" and line code "([^"]+)"')
def step_parsed_result(context, mode, line_code):
    assert context.parsed is not None, "Expected a parsed line query, got None"
    assert context.parsed.mode == mode, f"Expected mode {mode!r}, got {context.parsed.mode!r}"
    assert context.parsed.line_code == line_code, f"Expected line_code {line_code!r}, got {context.parsed.line_code!r}"


@then("no line query is parsed")
def step_no_query(context):
    assert context.parsed is None, f"Expected None, got {context.parsed}"
