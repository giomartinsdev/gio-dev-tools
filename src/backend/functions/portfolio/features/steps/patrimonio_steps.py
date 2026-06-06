from decimal import Decimal
from typing import Optional

from behave import given, then, use_step_matcher, when

from src.application.commands.create_asset import CreateAssetCommand, CreateAssetHandler
from src.application.commands.delete_asset import DeleteAssetCommand, DeleteAssetHandler
from src.application.commands.update_asset import UpdateAssetCommand, UpdateAssetHandler
from src.domain.asset import Asset
from src.domain.events import AssetCreated, AssetDeleted, AssetUpdated
from src.domain.repository import AssetRepository
from src.infrastructure.event_bus import EventBus

use_step_matcher("re")


class InMemoryAssetRepository(AssetRepository):
    def __init__(self):
        self._store: dict[str, Asset] = {}

    def save(self, asset: Asset) -> None:
        self._store[asset.id] = asset

    def delete(self, asset_id: str) -> bool:
        if asset_id in self._store:
            del self._store[asset_id]
            return True
        return False

    def find_all(self) -> list[Asset]:
        return list(self._store.values())

    def find_by_id(self, asset_id: str) -> Optional[Asset]:
        return self._store.get(asset_id)


def _setup(context):
    context.repo = InMemoryAssetRepository()
    context.bus = EventBus()
    context.published_events = []
    for event_type in (AssetCreated, AssetUpdated, AssetDeleted):
        context.bus.subscribe(event_type, lambda e: context.published_events.append(e))
    context.create_handler = CreateAssetHandler(context.repo, context.bus)
    context.update_handler = UpdateAssetHandler(context.repo, context.bus)
    context.delete_handler = DeleteAssetHandler(context.repo, context.bus)
    context.last_asset = None
    context.original_asset_id = None
    context.last_result = None
    context.last_error = None


# Given

@given('an empty asset repository')
def step_empty_repo(context):
    _setup(context)


@given(r'an asset with name "([^"]+)" type "([^"]+)" institution "([^"]+)" quantity "([^"]+)" price "([^"]+)" exists')
def step_asset_exists(context, name, a_type, institution, quantity, price):
    context.last_asset = context.create_handler.handle(
        CreateAssetCommand(name=name, type=a_type, institution=institution, quantity=quantity, purchase_price=price)
    )
    context.original_asset_id = context.last_asset.id
    context.published_events.clear()


# When — create

@when(r'I create an asset with name "([^"]+)" type "([^"]+)" institution "([^"]+)" quantity "([^"]+)" price "([^"]+)"')
def step_create_asset(context, name, a_type, institution, quantity, price):
    context.last_asset = context.create_handler.handle(
        CreateAssetCommand(name=name, type=a_type, institution=institution, quantity=quantity, purchase_price=price)
    )
    context.last_error = None


@when(r'I try to create an asset with name "([^"]*)" type "([^"]*)" institution "([^"]*)" quantity "([^"]*)" price "([^"]*)"')
def step_try_create_asset(context, name, a_type, institution, quantity, price):
    try:
        context.create_handler.handle(
            CreateAssetCommand(name=name, type=a_type, institution=institution, quantity=quantity, purchase_price=price)
        )
        context.last_error = None
    except Exception as e:
        context.last_error = e


# When — update

@when(r'I update the asset with name "([^"]+)" type "([^"]+)" institution "([^"]+)" quantity "([^"]+)" price "([^"]+)"')
def step_update_asset(context, name, a_type, institution, quantity, price):
    context.last_asset = context.update_handler.handle(
        UpdateAssetCommand(
            asset_id=context.last_asset.id,
            name=name, type=a_type, institution=institution,
            quantity=quantity, purchase_price=price,
        )
    )
    context.last_error = None


@when(r'I try to update the asset with name "([^"]*)" type "([^"]*)" institution "([^"]*)" quantity "([^"]*)" price "([^"]*)"')
def step_try_update_asset(context, name, a_type, institution, quantity, price):
    try:
        context.update_handler.handle(
            UpdateAssetCommand(
                asset_id=context.last_asset.id,
                name=name, type=a_type, institution=institution,
                quantity=quantity, purchase_price=price,
            )
        )
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(r'I update asset "([^"]+)" with name "([^"]+)" type "([^"]+)" institution "([^"]+)" quantity "([^"]+)" price "([^"]+)"')
def step_update_asset_by_id(context, asset_id, name, a_type, institution, quantity, price):
    context.last_result = context.update_handler.handle(
        UpdateAssetCommand(asset_id=asset_id, name=name, type=a_type, institution=institution,
                           quantity=quantity, purchase_price=price)
    )


# When — delete

@when(r'I delete the asset')
def step_delete_asset(context):
    context.last_result = context.delete_handler.handle(DeleteAssetCommand(asset_id=context.last_asset.id))


@when(r'I delete asset "([^"]+)"')
def step_delete_asset_by_id(context, asset_id):
    context.last_result = context.delete_handler.handle(DeleteAssetCommand(asset_id=asset_id))


# Then

@then(r'the asset is saved with name "([^"]+)" and type "([^"]+)"')
def step_asset_saved(context, name, a_type):
    assert context.last_asset is not None
    assert context.last_asset.name == name, f"Expected name '{name}', got '{context.last_asset.name}'"
    assert context.last_asset.type.value == a_type, f"Expected type '{a_type}', got '{context.last_asset.type.value}'"


@then(r'the total value is "([^"]+)"')
def step_total_value(context, expected):
    assert context.last_asset is not None
    assert context.last_asset.total_value == Decimal(expected), \
        f"Expected total_value {expected}, got {context.last_asset.total_value}"


@then(r'the repository has (\d+) asset')
def step_repo_count(context, count):
    assets = context.repo.find_all()
    assert len(assets) == int(count), f"Expected {count} asset(s), got {len(assets)}"


@then(r'the asset has name "([^"]+)" and quantity "([^"]+)"')
def step_asset_fields(context, name, quantity):
    assert context.last_asset is not None
    assert context.last_asset.name == name, f"Expected name '{name}', got '{context.last_asset.name}'"
    assert context.last_asset.quantity == Decimal(quantity), \
        f"Expected quantity {quantity}, got {context.last_asset.quantity}"


@then(r'the asset id changed')
def step_asset_id_changed(context):
    assert context.last_asset.id != context.original_asset_id, \
        "Expected a new asset id (immutable ledger), but id is unchanged"


@then(r'the asset repository is empty')
def step_repo_empty(context):
    assert not context.repo.find_all(), "Expected empty asset repository"


@then(r'an AssetCreated event is published')
def step_asset_created_event(context):
    events = [e for e in context.published_events if isinstance(e, AssetCreated)]
    assert events, f"Expected AssetCreated event; got: {context.published_events}"


@then(r'an AssetUpdated event is published')
def step_asset_updated_event(context):
    events = [e for e in context.published_events if isinstance(e, AssetUpdated)]
    assert events, f"Expected AssetUpdated event; got: {context.published_events}"


@then(r'an AssetDeleted event is published')
def step_asset_deleted_event(context):
    events = [e for e in context.published_events if isinstance(e, AssetDeleted)]
    assert events, f"Expected AssetDeleted event; got: {context.published_events}"


@then(r'a validation error contains "([^"]+)"')
def step_validation_error(context, message):
    assert context.last_error is not None, "Expected a validation error but none was raised"
    assert message in str(context.last_error), f"Expected '{message}' in error: {context.last_error}"


@then(r'the deletion returns false')
def step_deletion_false(context):
    assert context.last_result is False, f"Expected False, got {context.last_result}"


@then(r'no update is performed')
def step_no_update(context):
    assert context.last_result is None, f"Expected None, got {context.last_result}"
