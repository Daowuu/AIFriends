from __future__ import annotations

from typing import Any


GRAPH_VERSION = 1


def new_dag_runtime(*, graph_meta=None):
    return {
        'graph_version': GRAPH_VERSION,
        'nodes': {},
        'edges': [],
        'ready_nodes': [],
        'waiting_nodes': [],
        'completed_nodes': [],
        'failed_nodes': [],
        'node_payloads': {},
        'next_node_index': 1,
        'graph_meta': graph_meta if isinstance(graph_meta, dict) else {},
    }


def sanitize_node(raw_node):
    if not isinstance(raw_node, dict):
        return None
    node_id = str(raw_node.get('id') or '').strip()
    kind = str(raw_node.get('kind') or '').strip()
    if not node_id or not kind:
        return None
    phase = str(raw_node.get('phase') or '').strip()
    data = raw_node.get('data')
    meta = raw_node.get('meta')
    return {
        'id': node_id,
        'kind': kind,
        'phase': phase,
        'data': data if isinstance(data, dict) else {},
        'meta': meta if isinstance(meta, dict) else {},
    }


def sanitize_edge(raw_edge):
    if not isinstance(raw_edge, dict):
        return None
    from_node_id = str(raw_edge.get('from') or '').strip()
    to_node_id = str(raw_edge.get('to') or '').strip()
    if not from_node_id or not to_node_id:
        return None
    condition = raw_edge.get('condition')
    if condition is not None:
        condition = str(condition).strip() or None
    meta = raw_edge.get('meta')
    return {
        'from': from_node_id,
        'to': to_node_id,
        'condition': condition,
        'meta': meta if isinstance(meta, dict) else {},
    }


def is_compatible_dag_runtime(runtime):
    if not isinstance(runtime, dict):
        return False
    if int(runtime.get('graph_version', -1)) != GRAPH_VERSION:
        return False
    if not isinstance(runtime.get('nodes'), dict):
        return False
    if not isinstance(runtime.get('edges'), list):
        return False
    for key in ('ready_nodes', 'waiting_nodes', 'completed_nodes', 'failed_nodes'):
        if not isinstance(runtime.get(key), list):
            return False
    if not isinstance(runtime.get('node_payloads'), dict):
        return False
    return True


def sanitize_dag_runtime(runtime):
    if not is_compatible_dag_runtime(runtime):
        return new_dag_runtime()

    nodes = {}
    for raw_node in runtime.get('nodes', {}).values():
        node = sanitize_node(raw_node)
        if node:
            nodes[node['id']] = node

    edges = []
    for raw_edge in runtime.get('edges', []):
        edge = sanitize_edge(raw_edge)
        if edge:
            edges.append(edge)

    sanitized = {
        'graph_version': GRAPH_VERSION,
        'nodes': nodes,
        'edges': edges,
        'ready_nodes': [node_id for node_id in runtime.get('ready_nodes', []) if str(node_id).strip() in nodes],
        'waiting_nodes': [node_id for node_id in runtime.get('waiting_nodes', []) if str(node_id).strip() in nodes],
        'completed_nodes': [node_id for node_id in runtime.get('completed_nodes', []) if str(node_id).strip() in nodes],
        'failed_nodes': [node_id for node_id in runtime.get('failed_nodes', []) if str(node_id).strip() in nodes],
        'node_payloads': runtime.get('node_payloads') if isinstance(runtime.get('node_payloads'), dict) else {},
        'next_node_index': max(1, int(runtime.get('next_node_index', 1) or 1)),
        'graph_meta': runtime.get('graph_meta') if isinstance(runtime.get('graph_meta'), dict) else {},
    }
    _normalize_runtime_status_lists(sanitized)
    return sanitized


def next_node_id(runtime):
    next_index = max(1, int(runtime.get('next_node_index', 1) or 1))
    runtime['next_node_index'] = next_index + 1
    return f'node-{next_index}'


def get_node(runtime, node_id):
    return runtime.get('nodes', {}).get(str(node_id or '').strip())


def list_ready_nodes(runtime):
    return [get_node(runtime, node_id) for node_id in runtime.get('ready_nodes', []) if get_node(runtime, node_id)]


def peek_ready_node(runtime):
    for node_id in runtime.get('ready_nodes', []):
        node = get_node(runtime, node_id)
        if node:
            return node
    return None


def add_node(runtime, *, kind: str, phase: str, data=None, meta=None, node_id: str | None = None):
    node = {
        'id': str(node_id or next_node_id(runtime)).strip(),
        'kind': str(kind or '').strip(),
        'phase': str(phase or '').strip(),
        'data': data if isinstance(data, dict) else {},
        'meta': meta if isinstance(meta, dict) else {},
    }
    if not node['id'] or not node['kind']:
        raise ValueError('DAG 节点必须包含 id 和 kind。')
    if node['id'] in runtime.setdefault('nodes', {}):
        raise ValueError(f"DAG 节点重复：{node['id']}")
    runtime['nodes'][node['id']] = node
    return node


def add_edge(runtime, *, from_node_id: str, to_node_id: str, condition=None, meta=None):
    edge = {
        'from': str(from_node_id or '').strip(),
        'to': str(to_node_id or '').strip(),
        'condition': str(condition).strip() if condition is not None and str(condition).strip() else None,
        'meta': meta if isinstance(meta, dict) else {},
    }
    if not edge['from'] or not edge['to']:
        raise ValueError('DAG 边必须包含 from 和 to。')
    runtime.setdefault('edges', []).append(edge)
    return edge


def initialize_runtime(runtime):
    validate_dag_runtime(runtime)
    _recompute_runtime_state(runtime)
    return runtime


def append_dynamic_node(runtime, *, kind: str, phase: str, data=None, meta=None, depends_on=None, condition=None, node_id: str | None = None):
    node = add_node(runtime, kind=kind, phase=phase, data=data, meta=meta, node_id=node_id)
    dependency_ids = _normalize_dependency_ids(depends_on)
    for dependency_id in dependency_ids:
        add_edge(runtime, from_node_id=dependency_id, to_node_id=node['id'], condition=condition)
    validate_dag_runtime(runtime)
    _recompute_runtime_state(runtime)
    return node


def pop_ready_node(runtime):
    ready_nodes = runtime.setdefault('ready_nodes', [])
    while ready_nodes:
        node_id = ready_nodes.pop(0)
        node = get_node(runtime, node_id)
        if node:
            return node
    return None


def mark_node_completed(runtime, node, payload=None):
    node_id = str(node.get('id') or '').strip()
    if not node_id:
        raise ValueError('无效 DAG 节点。')
    runtime.setdefault('node_payloads', {})[node_id] = payload if isinstance(payload, dict) else {}
    if node_id not in runtime.setdefault('completed_nodes', []):
        runtime['completed_nodes'].append(node_id)
    _remove_node_id_from_lists(runtime, node_id, exclude='completed_nodes')
    _recompute_runtime_state(runtime)
    return get_node(runtime, node_id)


def mark_node_failed(runtime, node, payload=None):
    node_id = str(node.get('id') or '').strip()
    if not node_id:
        raise ValueError('无效 DAG 节点。')
    runtime.setdefault('node_payloads', {})[node_id] = payload if isinstance(payload, dict) else {}
    if node_id not in runtime.setdefault('failed_nodes', []):
        runtime['failed_nodes'].append(node_id)
    _remove_node_id_from_lists(runtime, node_id, exclude='failed_nodes')
    _recompute_runtime_state(runtime)
    return get_node(runtime, node_id)


def retry_failed_node(runtime, node_id):
    normalized_node_id = str(node_id or '').strip()
    if not normalized_node_id:
        raise ValueError('无效 DAG 节点。')
    runtime['failed_nodes'] = [existing_id for existing_id in runtime.get('failed_nodes', []) if existing_id != normalized_node_id]
    runtime.setdefault('node_payloads', {}).pop(normalized_node_id, None)
    _recompute_runtime_state(runtime)
    return get_node(runtime, normalized_node_id)


def validate_dag_runtime(runtime):
    nodes = runtime.get('nodes', {})
    if not isinstance(nodes, dict):
        raise ValueError('DAG nodes 必须是对象。')
    node_ids = set(nodes.keys())
    for node_id, raw_node in nodes.items():
        node = sanitize_node(raw_node)
        if not node or node['id'] != node_id:
            raise ValueError(f'存在无效 DAG 节点：{node_id}')

    for raw_edge in runtime.get('edges', []):
        edge = sanitize_edge(raw_edge)
        if not edge:
            raise ValueError('存在无效 DAG 边。')
        if edge['from'] not in node_ids or edge['to'] not in node_ids:
            raise ValueError('DAG 边引用了不存在的节点。')

    _validate_acyclic_graph(node_ids, runtime.get('edges', []))
    return True


def _normalize_runtime_status_lists(runtime):
    node_ids = set(runtime.get('nodes', {}).keys())
    normalized_lists = {}
    seen = set()
    for key in ('completed_nodes', 'failed_nodes', 'ready_nodes', 'waiting_nodes'):
        items = []
        for raw_node_id in runtime.get(key, []):
            node_id = str(raw_node_id or '').strip()
            if not node_id or node_id not in node_ids or node_id in seen:
                continue
            items.append(node_id)
            seen.add(node_id)
        normalized_lists[key] = items
    runtime.update(normalized_lists)


def _normalize_dependency_ids(depends_on):
    if depends_on is None:
        return []
    if isinstance(depends_on, (list, tuple, set)):
        values = depends_on
    else:
        values = [depends_on]
    return [str(value).strip() for value in values if str(value).strip()]


def _remove_node_id_from_lists(runtime, node_id, *, exclude=None):
    for key in ('ready_nodes', 'waiting_nodes', 'completed_nodes', 'failed_nodes'):
        if key == exclude:
            continue
        runtime[key] = [existing_id for existing_id in runtime.get(key, []) if existing_id != node_id]


def _edge_condition_matches(payload, condition):
    if condition in (None, ''):
        return True
    if not isinstance(payload, dict):
        return False
    outcome = payload.get('route')
    if outcome is None:
        outcome = payload.get('outcome')
    if isinstance(outcome, (list, tuple, set)):
        return str(condition) in {str(item) for item in outcome}
    return str(outcome or '') == str(condition)


def _node_dependencies_satisfied(runtime, node_id):
    inbound_edges = [edge for edge in runtime.get('edges', []) if edge['to'] == node_id]
    if not inbound_edges:
        return True

    completed_ids = set(runtime.get('completed_nodes', []))
    payloads = runtime.get('node_payloads', {})
    for edge in inbound_edges:
        if edge['from'] not in completed_ids:
            return False
        if not _edge_condition_matches(payloads.get(edge['from'], {}), edge.get('condition')):
            return False
    return True


def _recompute_runtime_state(runtime):
    _normalize_runtime_status_lists(runtime)
    node_ids = set(runtime.get('nodes', {}).keys())
    completed_ids = set(runtime.get('completed_nodes', []))
    failed_ids = set(runtime.get('failed_nodes', []))

    ready_ids = []
    waiting_ids = []
    for node_id in node_ids:
        if node_id in completed_ids or node_id in failed_ids:
            continue
        if _node_dependencies_satisfied(runtime, node_id):
            ready_ids.append(node_id)
        else:
            waiting_ids.append(node_id)

    runtime['ready_nodes'] = sorted(ready_ids, key=_runtime_node_sort_key(runtime))
    runtime['waiting_nodes'] = sorted(waiting_ids, key=_runtime_node_sort_key(runtime))
    return runtime


def _runtime_node_sort_key(runtime):
    def sort_key(node_id):
        node = get_node(runtime, node_id) or {}
        numeric_id = 10**9
        parts = str(node_id).split('-')
        if len(parts) == 2 and parts[1].isdigit():
            numeric_id = int(parts[1])
        return (numeric_id, node.get('kind', ''), node_id)

    return sort_key


def _validate_acyclic_graph(node_ids, edges):
    incoming = {node_id: 0 for node_id in node_ids}
    outgoing = {node_id: [] for node_id in node_ids}
    for raw_edge in edges:
        edge = sanitize_edge(raw_edge)
        if not edge:
            continue
        incoming[edge['to']] += 1
        outgoing[edge['from']].append(edge['to'])

    queue = [node_id for node_id, count in incoming.items() if count == 0]
    visited = 0
    while queue:
        node_id = queue.pop(0)
        visited += 1
        for target_id in outgoing[node_id]:
            incoming[target_id] -= 1
            if incoming[target_id] == 0:
                queue.append(target_id)

    if visited != len(node_ids):
        raise ValueError('DAG 中检测到环，当前图不是合法拓扑结构。')
