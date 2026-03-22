from __future__ import annotations

from web.dag_runtime import append_dynamic_node, initialize_runtime, new_dag_runtime


class NodeKind:
    MODERATOR_OPENING = 'discussion_moderator_opening'
    AGENDA_SETUP = 'discussion_agenda_setup'
    OPENING_TURN = 'discussion_opening_turn'
    ROUND_SUMMARY = 'discussion_round_summary'
    FOCUSED_TURN = 'discussion_focused_turn'
    CONSENSUS_DRAFT = 'discussion_consensus_draft'
    FINAL_RESPONSE_TURN = 'discussion_final_response_turn'
    FINISH = 'discussion_finish'


def build_initial_discussion_dag_runtime(*, participant_ids, moderator_seat_id: int, max_rounds: int):
    runtime = new_dag_runtime(graph_meta={
        'domain': 'discussion',
        'max_rounds': int(max_rounds),
        'moderator_seat_id': int(moderator_seat_id),
    })
    opening_node = append_dynamic_node(
        runtime,
        kind=NodeKind.MODERATOR_OPENING,
        phase='day_speeches',
        data={
            'round_number': 1,
            'stage': 'topic_opening',
            'moderator_seat_id': int(moderator_seat_id),
            'participant_ids': [int(seat_id) for seat_id in participant_ids],
        },
    )
    agenda_node = append_dynamic_node(
        runtime,
        kind=NodeKind.AGENDA_SETUP,
        phase='day_speeches',
        data={
            'round_number': 1,
            'stage': 'agenda_setup',
            'moderator_seat_id': int(moderator_seat_id),
            'participant_ids': [int(seat_id) for seat_id in participant_ids],
        },
        depends_on=opening_node['id'],
    )
    append_opening_round(
        runtime,
        round_number=1,
        participant_ids=participant_ids,
        depends_on=agenda_node['id'],
    )
    initialize_runtime(runtime)
    return runtime


def append_opening_round(runtime, *, round_number: int, participant_ids, depends_on=None):
    return _append_discussion_round(
        runtime,
        round_number=round_number,
        participant_ids=participant_ids,
        turn_kind=NodeKind.OPENING_TURN,
        stage='opening_turn',
        summary_stage='round_summary',
        depends_on=depends_on,
    )


def append_focused_round(runtime, *, round_number: int, participant_ids, depends_on=None):
    return _append_discussion_round(
        runtime,
        round_number=round_number,
        participant_ids=participant_ids,
        turn_kind=NodeKind.FOCUSED_TURN,
        stage='focused_turn',
        summary_stage='round_summary',
        depends_on=depends_on,
    )


def append_final_response_round(runtime, *, round_number: int, participant_ids, depends_on=None):
    previous_node_id = depends_on
    turn_nodes = []
    for turn_index, seat_id in enumerate([int(value) for value in participant_ids], start=1):
        turn_node = append_dynamic_node(
            runtime,
            kind=NodeKind.FINAL_RESPONSE_TURN,
            phase='day_speeches',
            data={
                'round_number': int(round_number),
                'participant_ids': [int(value) for value in participant_ids],
                'turn_index': turn_index,
                'seat_id': int(seat_id),
                'stage': 'final_response_turn',
            },
            depends_on=previous_node_id,
        )
        turn_nodes.append(turn_node)
        previous_node_id = turn_node['id']
    return {
        'turn_nodes': turn_nodes,
        'last_node_id': previous_node_id,
    }


def append_consensus_draft(runtime, *, round_number: int, depends_on=None):
    return append_dynamic_node(
        runtime,
        kind=NodeKind.CONSENSUS_DRAFT,
        phase='day_speeches',
        data={
            'round_number': int(round_number),
            'stage': 'consensus_draft',
            'moderator_seat_id': int(runtime.get('graph_meta', {}).get('moderator_seat_id') or 0),
        },
        depends_on=depends_on,
    )


def append_discussion_finish(runtime, *, round_number: int, depends_on=None):
    return append_dynamic_node(
        runtime,
        kind=NodeKind.FINISH,
        phase='finished',
        data={
            'round_number': int(round_number),
            'stage': 'discussion_finish',
            'moderator_seat_id': int(runtime.get('graph_meta', {}).get('moderator_seat_id') or 0),
        },
        depends_on=depends_on,
    )


def _append_discussion_round(runtime, *, round_number: int, participant_ids, turn_kind: str, stage: str, summary_stage: str, depends_on=None):
    normalized_participant_ids = [int(seat_id) for seat_id in participant_ids]
    previous_node_id = depends_on
    turn_nodes = []
    for turn_index, seat_id in enumerate(normalized_participant_ids, start=1):
        turn_node = append_dynamic_node(
            runtime,
            kind=turn_kind,
            phase='day_speeches',
            data={
                'round_number': int(round_number),
                'participant_ids': normalized_participant_ids[:],
                'turn_index': turn_index,
                'seat_id': int(seat_id),
                'stage': stage,
            },
            depends_on=previous_node_id,
        )
        turn_nodes.append(turn_node)
        previous_node_id = turn_node['id']
    summary_node = append_dynamic_node(
        runtime,
        kind=NodeKind.ROUND_SUMMARY,
        phase='day_speeches',
        data={
            'round_number': int(round_number),
            'participant_ids': normalized_participant_ids[:],
            'stage': summary_stage,
            'source_stage': stage,
            'moderator_seat_id': int(runtime.get('graph_meta', {}).get('moderator_seat_id') or 0),
        },
        depends_on=previous_node_id,
    )
    return {
        'turn_nodes': turn_nodes,
        'summary_node': summary_node,
    }
