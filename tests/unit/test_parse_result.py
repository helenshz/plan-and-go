"""Spec 0002 acceptance criteria 5 and 6: parse result validation and JSON Schema."""

import json

import pytest
from pydantic import ValidationError

from plan_and_go.parse_result import ParseResult


def _minimal(**overrides):
    data = {
        'scale': {'p1': [0, 0], 'p2': [100, 0], 'meters': 1.0},
        'walls': [{'p1': [0, 0], 'p2': [100, 0], 'thickness': 10}],
        'doors': [],
        'rooms': [],
    }
    data.update(overrides)
    return data


def test_minimal_parse_result_is_valid():
    ParseResult.model_validate(_minimal())


@pytest.mark.parametrize('overrides, message', [
    ({'walls': [{'p1': [5, 5], 'p2': [5, 5], 'thickness': 10}]}, 'zero length'),
    ({'walls': [{'p1': [0, 0], 'p2': [9, 0], 'thickness': 0}]}, 'greater than 0'),
    ({'walls': []}, 'at least 1'),
    ({'scale': {'p1': [0, 0], 'p2': [100, 0], 'meters': 0}}, 'greater than 0'),
    ({'scale': {'p1': [3, 3], 'p2': [3, 3], 'meters': 1}}, 'must differ'),
    ({'rooms': [{'name': 'kitchen', 'at': [1, 1]}, {'name': 'kitchen', 'at': [2, 2]}]},
     'unique'),
    ({'rooms': [{'name': 'x', 'at': [1, 1]}],
      'doors': [{'name': 'x', 'p1': [10, 0], 'p2': [20, 0]}]}, 'unique'),
    ({'rooms': [{'name': 'living room', 'at': [1, 1]}]}, 'pattern'),
    ({'doors': [{'name': 'd', 'p1': [10, 0], 'p2': [10, 0]}]}, 'zero length'),
    ({'doors': [{'name': 'd', 'p1': [10, 0], 'p2': [20, 0], 'type': 'revolving'}]}, 'hinged'),
    ({'furniture': []}, 'Extra inputs'),
])
def test_invalid_parse_results_are_rejected(overrides, message):
    with pytest.raises(ValidationError, match=message):
        ParseResult.model_validate(_minimal(**overrides))


def test_door_type_defaults_to_hinged():
    pr = ParseResult.model_validate(
        _minimal(doors=[{'name': 'd', 'p1': [10, 0], 'p2': [20, 0]}]))
    assert pr.doors[0].type == 'hinged'


def test_json_schema_export():
    schema = ParseResult.model_json_schema()
    json.dumps(schema)  # serialisable
    assert set(schema['required']) == {'scale', 'walls'}
    assert {'Wall', 'Door', 'Room', 'Scale'} <= set(schema['$defs'])
