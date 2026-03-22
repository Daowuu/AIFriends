import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings

from web.ai_settings_service import (
    RUNTIME_STORE_ENV_KEY,
    get_current_runtime_settings,
    get_runtime_ai_resolution,
)
from web.dag_runtime import (
    GRAPH_VERSION,
    append_dynamic_node,
    initialize_runtime,
    mark_node_completed,
    new_dag_runtime,
    peek_ready_node,
    pop_ready_node,
)
from web.discussion_services import (
    _contains_off_topic_or_leakage,
    advance_discussion_group,
    create_discussion_group,
    reset_discussion_group,
)
from web.local_runtime import (
    ELYSIA_DEMO_VOICE_CODE,
    ensure_default_characters,
    ensure_demo_voice_configs,
    get_or_create_local_operator_user,
)
from web.models import Character, Voice, WerewolfGame, WerewolfSpeech
from web.openai_compat import create_chat_completion


class OpenAICompatTests(TestCase):
    def test_create_chat_completion_retries_with_max_completion_tokens(self):
        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                if 'max_tokens' in kwargs:
                    raise Exception("Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.")
                return {'ok': True}

        class FakeChat:
            completions = FakeCompletions()

        class FakeClient:
            chat = FakeChat()

        result = create_chat_completion(
            FakeClient(),
            model='test-model',
            messages=[{'role': 'user', 'content': 'ping'}],
            max_tokens=16,
        )

        self.assertEqual(result, {'ok': True})
        self.assertEqual(len(calls), 2)
        self.assertIn('max_tokens', calls[0])
        self.assertNotIn('max_tokens', calls[1])
        self.assertEqual(calls[1].get('max_completion_tokens'), 16)


class DagRuntimeTests(TestCase):
    def test_initialize_runtime_marks_zero_indegree_node_ready(self):
        runtime = new_dag_runtime(graph_meta={'domain': 'test'})
        first = append_dynamic_node(runtime, kind='start', phase='alpha')
        second = append_dynamic_node(runtime, kind='next', phase='beta', depends_on=first['id'])

        initialize_runtime(runtime)

        self.assertEqual(runtime['graph_version'], GRAPH_VERSION)
        self.assertEqual(runtime['ready_nodes'], [first['id']])
        self.assertIn(second['id'], runtime['waiting_nodes'])

    def test_mark_node_completed_promotes_successor(self):
        runtime = new_dag_runtime()
        first = append_dynamic_node(runtime, kind='start', phase='alpha')
        second = append_dynamic_node(runtime, kind='next', phase='beta', depends_on=first['id'])

        initialize_runtime(runtime)
        node = pop_ready_node(runtime)
        mark_node_completed(runtime, node, {'outcome': 'done'})

        self.assertEqual(runtime['completed_nodes'], [first['id']])
        self.assertEqual(peek_ready_node(runtime)['id'], second['id'])

    def test_condition_edge_only_activates_matching_successor(self):
        runtime = new_dag_runtime()
        start = append_dynamic_node(runtime, kind='start', phase='alpha')
        yes_node = append_dynamic_node(runtime, kind='yes', phase='beta', depends_on=start['id'], condition='yes')
        no_node = append_dynamic_node(runtime, kind='no', phase='beta', depends_on=start['id'], condition='no')

        initialize_runtime(runtime)
        node = pop_ready_node(runtime)
        mark_node_completed(runtime, node, {'route': 'yes'})

        self.assertEqual(peek_ready_node(runtime)['id'], yes_node['id'])
        self.assertIn(no_node['id'], runtime['waiting_nodes'])

    def test_initialize_runtime_rejects_cycle(self):
        runtime = new_dag_runtime()
        first = append_dynamic_node(runtime, kind='first', phase='alpha')
        second = append_dynamic_node(runtime, kind='second', phase='beta', depends_on=first['id'])
        runtime['edges'].append({
            'from': second['id'],
            'to': first['id'],
            'condition': None,
            'meta': {},
        })

        with self.assertRaisesMessage(ValueError, '不是合法拓扑结构'):
            initialize_runtime(runtime)


class CharacterSeedTests(TestCase):
    def test_character_list_auto_seeds_builtin_characters(self):
        self.assertEqual(Character.objects.count(), 0)

        response = self.client.get('/api/character/list/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload['characters']), 15)
        self.assertEqual(payload['characters'][0]['name'], '爱莉希雅')
        self.assertTrue(any(character['name'] == '凯文' for character in payload['characters']))
        self.assertTrue(any(character['name'] == '雷电芽衣' for character in payload['characters']))
        self.assertEqual(Character.objects.filter(user=get_or_create_local_operator_user()).count(), len(payload['characters']))

    def test_builtin_seed_preserves_elysia_media_and_voice(self):
        ensure_default_characters()

        elysia = Character.objects.get(name='爱莉希雅')
        self.assertTrue(elysia.photo.name.endswith('elysia-avatar.png'))
        self.assertTrue(elysia.background_image.name.endswith('elysia-background.webp'))
        self.assertIsNotNone(elysia.voice)
        self.assertEqual(elysia.voice.voice_code, ELYSIA_DEMO_VOICE_CODE)


class RuntimeEnvSettingsTests(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / '.env'
        self.override = override_settings(AI_RUNTIME_ENV_PATH=str(self.env_path))
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.temp_dir.cleanup()
        super().tearDown()

    def test_runtime_settings_save_creates_provider_keyed_env_store(self):
        response = self.client.post(
            '/api/runtime/settings/',
            data=json.dumps({
                'provider': 'openai',
                'api_base': 'https://api.openai.com/v1',
                'model_name': 'gpt-5.4',
                'api_key': 'sk-openai',
                'asr_api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                'asr_model_name': 'qwen3-asr-flash',
                'asr_api_key': 'dashscope-a',
                'tts_model_name': 'cosyvoice-v3.5-plus',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['settings']['provider'], 'openai')
        self.assertEqual(payload['settings']['source'], 'runtime_env')
        self.assertEqual(len(payload['chat_providers']), 1)

        resolution = get_runtime_ai_resolution()
        self.assertEqual(resolution['status'], 'ok')
        self.assertEqual(resolution['config']['provider'], 'openai')
        self.assertEqual(resolution['config']['model_name'], 'gpt-5.4')

        env_text = self.env_path.read_text(encoding='utf-8')
        self.assertIn(RUNTIME_STORE_ENV_KEY, env_text)
        self.assertIn('\n  "chat": {\n', env_text)
        self.assertIn('\n  "voice": {\n', env_text)

        env_store = json.loads(dotenv_values(self.env_path)[RUNTIME_STORE_ENV_KEY])
        self.assertEqual(env_store['version'], 4)
        self.assertEqual(env_store['active']['chat_provider'], 'openai')
        self.assertEqual(env_store['chat']['openai']['model_name'], 'gpt-5.4')
        self.assertEqual(env_store['api_keys']['openai'], 'sk-openai')
        self.assertEqual(env_store['api_keys']['aliyun_voice'], 'dashscope-a')

    def test_runtime_settings_save_minimax_preserves_openai_slot(self):
        self.env_path.write_text(
            "AI_RUNTIME_CONFIG_JSON='{\n"
            '  "version": 4,\n'
            '  "active": {\n'
            '    "chat_provider": "openai"\n'
            '  },\n'
            '  "api_keys": {\n'
            '    "openai": "sk-openai",\n'
            '    "aliyun_voice": "dashscope-a"\n'
            '  },\n'
            '  "chat": {\n'
            '    "openai": {\n'
            '      "api_base": "https://api.openai.com/v1",\n'
            '      "model_name": "gpt-5.4",\n'
            '      "updated_at": "2026-03-22T00:00:00+08:00"\n'
            '    }\n'
            '  },\n'
            '  "voice": {\n'
            '    "provider": "aliyun",\n'
            '    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",\n'
            '    "asr_model_name": "qwen3-asr-flash",\n'
            '    "tts_model_name": "cosyvoice-v3.5-plus",\n'
            '    "updated_at": "2026-03-22T00:00:00+08:00"\n'
            '  }\n'
            "}'\n",
            encoding='utf-8',
        )

        response = self.client.post(
            '/api/runtime/settings/',
            data=json.dumps({
                'provider': 'minimax',
                'api_base': 'https://api.minimaxi.com/v1',
                'model_name': 'MiniMax-M2.7-highspeed',
                'api_key': 'sk-minimax',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        env_store = json.loads(dotenv_values(self.env_path)[RUNTIME_STORE_ENV_KEY])
        self.assertEqual(env_store['active']['chat_provider'], 'minimax')
        self.assertEqual(env_store['chat']['openai']['model_name'], 'gpt-5.4')
        self.assertEqual(env_store['chat']['minimax']['model_name'], 'MiniMax-M2.7-highspeed')
        self.assertEqual(env_store['api_keys']['openai'], 'sk-openai')
        self.assertEqual(env_store['api_keys']['minimax'], 'sk-minimax')

    def test_get_current_runtime_settings_returns_empty_without_env_store(self):
        settings = get_current_runtime_settings()
        self.assertFalse(settings.enabled)
        self.assertEqual(settings.provider, 'openai')
        self.assertEqual(settings.api_key, '')


class LocalRuntimeTests(TestCase):
    def test_ensure_demo_voice_configs_keeps_single_plus_demo_voice(self):
        ensure_demo_voice_configs()
        ensure_demo_voice_configs()

        local_user = get_or_create_local_operator_user()
        voices = Voice.objects.filter(owner=local_user, voice_code=ELYSIA_DEMO_VOICE_CODE)
        self.assertEqual(voices.count(), 1)
        self.assertEqual(voices.first().model_name, 'cosyvoice-v3.5-plus')


class DiscussionFlowTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = get_or_create_local_operator_user()
        self.characters = [
            Character.objects.create(user=self.user, name='爱莉希雅', profile='偏乐观，喜欢抛出开放问题。'),
            Character.objects.create(user=self.user, name='符华', profile='偏理性，习惯拆解问题。'),
            Character.objects.create(user=self.user, name='布洛妮娅', profile='偏冷静，善于总结方案。'),
        ]

    def _create_group(self, *, count=3, max_rounds=2):
        with patch('web.discussion_services._pick_round_start_index', return_value=0):
            return create_discussion_group(
                title='测试讨论组',
                topic='AI 角色如何开展高质量群体讨论？',
                character_ids=[character.id for character in self.characters[:count]],
                max_rounds=max_rounds,
            )

    def _moderator_payload(self, seat, *, stage, round_number=1, **_kwargs):
        if stage == 'topic_opening':
            return {
                'content': f'{seat.display_name}：这次先别急着给结论。请先回答一个问题：什么情况才算角色讨论已经同质化了？',
                'round_goal': '先明确问题边界。',
                'new_focus': '先判断什么叫内容同质化。',
                'agenda_items': ['定义什么叫同质化', '讨论如何制造角色差异'],
                'resolved_points': [],
                'open_questions': ['不同角色应该在哪一层体现差异？'],
                'consensus_draft': '',
                'route': '',
                'avoid_repeating': ['不要重复主题本身'],
            }
        if stage == 'agenda_setup':
            return {
                'content': f'{seat.display_name}：我先把议题拆开：第一，怎么定义同质化；第二，怎样让角色差异真的落到讨论里。请大家先说初始立场。',
                'round_goal': '先让角色表达各自初始立场。',
                'new_focus': '请每个人先给出自己最关注的判断标准。',
                'agenda_items': ['定义什么叫同质化', '讨论如何制造角色差异'],
                'resolved_points': [],
                'open_questions': ['不同角色应该在哪一层体现差异？'],
                'consensus_draft': '',
                'route': '',
                'avoid_repeating': ['不要只说先界定边界'],
            }
        if stage == 'round_summary':
            if round_number >= 2:
                return {
                    'content': f'{seat.display_name}：第二轮之后，真正剩下的问题只有一个：先改角色目标，还是先改流程约束。下面我直接把它收束成可执行共识。',
                    'round_goal': '围绕核心分歧继续推进。',
                    'new_focus': '把主要分歧收束为可执行结论。',
                    'agenda_items': ['定义什么叫同质化', '讨论如何制造角色差异'],
                    'resolved_points': ['大家都认为不能只靠语气区分角色。'],
                    'open_questions': ['最终应该先改角色目标还是流程约束？'],
                    'consensus_draft': '',
                    'route': 'consensus',
                    'avoid_repeating': ['不要重复上一轮总结'],
                }
            return {
                'content': f'{seat.display_name}：这一轮先收束成两个结果：已经确认不能只靠语气区分角色；真正的分歧在于要先改角色目标还是先改流程约束。下一轮请正面回答：到底该优先区分角色目标，还是区分表达策略？',
                'round_goal': '围绕核心分歧继续推进。',
                'new_focus': '到底该优先区分角色目标，还是区分表达策略？',
                'agenda_items': ['定义什么叫同质化', '讨论如何制造角色差异'],
                'resolved_points': ['大家都认为不能只靠语气区分角色。'],
                'open_questions': ['应该优先区分角色目标还是表达策略？'],
                'consensus_draft': '',
                'route': 'continue',
                'avoid_repeating': ['不要重复开场总结'],
            }
        return {
            'content': f'{seat.display_name}：最后我给出可执行共识：先让角色带着不同目标和利益进入讨论，再在流程上强制每轮补充新信息和回应对象。',
            'round_goal': '收束成可执行结论。',
            'new_focus': '把可执行结论收束出来。',
            'agenda_items': ['定义什么叫同质化', '讨论如何制造角色差异'],
            'resolved_points': ['大家都认为不能只靠语气区分角色。'],
            'open_questions': ['最终先改角色目标还是改流程约束？'],
            'consensus_draft': '先给角色明确目标和冲突，再用流程约束避免重复。',
            'route': 'finish',
            'avoid_repeating': ['不要重复前轮总结'],
        }

    def _participant_plan(self, seat, *, stage, **_kwargs):
        base = {
            'response_target': '',
            'agenda_item': '讨论如何制造角色差异',
            'stance_label': '中立分析',
            'avoid_repeating': ['不要重复边界和代价这类套话'],
        }
        if stage == 'opening_turn':
            return {
                **base,
                'new_information': f'{seat.display_name}认为差异首先应该体现在角色目标，而不是单纯口吻。',
            }
        if seat.display_name == '布洛妮娅':
            return {
                **base,
                'response_target': '符华',
                'new_information': '需要把“角色目标差异”进一步细化成判断标准，否则执行时还是会同质化。',
                'stance_label': '谨慎保留',
            }
        return {
            **base,
            'response_target': '',
            'new_information': f'{seat.display_name}补充：除了角色目标，还要约束每轮必须新增信息，否则还是会重复。',
            'stance_label': '支持推进',
        }

    def _participant_content(self, seat, *, plan, **_kwargs):
        response_target = str(plan.get('response_target') or '').strip()
        lead_map = {
            '爱莉希雅': '我更在意角色到底带着什么目标进入讨论。',
            '符华': '我更担心执行层如果没有硬约束，最后还是会收敛成模板话。',
            '布洛妮娅': '我会直接看流程有没有强制新增信息和回应对象。',
        }
        lead = lead_map.get(seat.display_name, '我先补一个更具体的角度。')
        if response_target:
            return f'{lead}{response_target}刚才提到的角色差异问题值得接着说。我的补充是：{plan["new_information"]}'
        return f'{lead}我的初步判断是：关于角色差异，{plan["new_information"]}'

    def test_create_discussion_group_initializes_structured_state_and_dag_runtime(self):
        group = self._create_group()
        runtime = group.state['dag_runtime']

        self.assertEqual(group.status, 'waiting')
        self.assertEqual(group.phase, 'setup')
        self.assertEqual(group.state['mode'], 'discussion')
        self.assertEqual(group.state['topic'], 'AI 角色如何开展高质量群体讨论？')
        self.assertEqual(group.state['max_rounds'], 2)
        self.assertIn('discussion_plan', group.state)
        self.assertIn('stance_map', group.state)
        self.assertIn('consensus_state', group.state)
        self.assertEqual(group.state['runtime_status'], 'ready')
        self.assertEqual(group.state['moderator_seat_id'], group.seats.order_by('seat_order', 'id').first().id)
        self.assertIn('dag_runtime', group.state)
        self.assertEqual(peek_ready_node(runtime)['kind'], 'discussion_moderator_opening')
        self.assertEqual(group.seats.count(), 3)
        self.assertEqual(group.events.count(), 1)
        self.assertEqual(group.events.first().event_type, 'game_created')

    def test_create_discussion_group_api_requires_topic(self):
        response = self.client.post(
            '/api/discussion/groups/create/',
            data=json.dumps({
                'title': '空主题',
                'topic': '',
                'character_ids': [character.id for character in self.characters[:2]],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('讨论主题不能为空', response.json()['detail'])

    def test_second_opening_turn_only_receives_prior_public_speeches(self):
        group = self._create_group()
        captured_public_states = []

        def fake_generate(_seat, *, public_state, plan, **_kwargs):
            captured_public_states.append(public_state)
            return f'关于角色差异，我认为{plan["new_information"]}'

        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=fake_generate):
            advance_discussion_group(group)  # moderator opening
            advance_discussion_group(group)  # agenda setup
            advance_discussion_group(group)  # first opening turn
            advance_discussion_group(group)  # second opening turn

        self.assertEqual(len(captured_public_states), 2)
        self.assertIn('爱莉希雅：爱莉希雅：这次先别急着给结论。', captured_public_states[0])
        self.assertIn('爱莉希雅：爱莉希雅：我先把议题拆开', captured_public_states[0])
        self.assertIn('当前阶段：角色立场', captured_public_states[0])
        self.assertIn('符华：关于角色差异', captured_public_states[1])
        self.assertNotIn('布洛妮娅：', captured_public_states[1])

    def test_moderator_nodes_also_create_public_speeches(self):
        group = self._create_group()

        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload):
            advance_discussion_group(group)
            advance_discussion_group(group)

        group.refresh_from_db()
        speeches = list(group.speeches.order_by('id'))
        self.assertEqual(len(speeches), 2)
        self.assertTrue(all(speech.audience == 'public' for speech in speeches))
        self.assertTrue(all(speech.seat.display_name == '爱莉希雅' for speech in speeches))
        self.assertTrue(all(speech.metadata.get('is_moderator_speech') is True for speech in speeches))
        self.assertEqual(speeches[0].metadata.get('stage'), 'topic_opening')
        self.assertEqual(speeches[1].metadata.get('stage'), 'agenda_setup')

    def test_duplicate_content_blocks_group_instead_of_using_fallback(self):
        group = self._create_group()
        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=[
                 '爱莉希雅认为，关于角色差异，首先该区分角色目标，而不是单纯语气。',
                 '爱莉希雅认为，关于角色差异，首先该区分角色目标，而不是单纯语气。',
             ]):
            advance_discussion_group(group)  # moderator opening
            advance_discussion_group(group)  # agenda setup
            advance_discussion_group(group)  # 爱莉希雅
            response = self.client.post(f'/api/discussion/groups/{group.id}/advance/', data=json.dumps({}), content_type='application/json')

        self.assertEqual(response.status_code, 400)
        group.refresh_from_db()
        self.assertEqual(group.state['runtime_status'], 'blocked')
        self.assertEqual(group.speeches.count(), 3)
        self.assertEqual(group.state['last_failure']['failure_code'], 'duplicate_content')
        self.assertEqual(group.events.last().event_type, 'node_failed')

    def test_too_short_content_blocks_group(self):
        group = self._create_group()
        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', return_value='嗯，那么'):
            advance_discussion_group(group)
            advance_discussion_group(group)
            response = self.client.post(f'/api/discussion/groups/{group.id}/advance/', data=json.dumps({}), content_type='application/json')

        self.assertEqual(response.status_code, 400)
        group.refresh_from_db()
        self.assertEqual(group.state['runtime_status'], 'blocked')
        self.assertEqual(group.state['last_failure']['failure_code'], 'too_short')
        self.assertEqual(group.speeches.count(), 2)

    def test_focused_turn_can_reply_without_explicitly_naming_target(self):
        group = self._create_group()

        def participant_plan(seat, *, stage, **_kwargs):
            if stage == 'opening_turn':
                return {
                    'response_target': '',
                    'agenda_item': '讨论如何制造角色差异',
                    'stance_label': '中立分析',
                    'avoid_repeating': [],
                    'new_information': f'{seat.display_name}先给出开场判断。',
                }
            if seat.display_name == '布洛妮娅':
                return {
                    'response_target': '符华',
                    'agenda_item': '讨论如何制造角色差异',
                    'stance_label': '支持推进',
                    'avoid_repeating': [],
                    'new_information': '我补充一个更具体的执行标准：每轮必须新增信息，而不是只重复立场。',
                }
            return {
                'response_target': '',
                'agenda_item': '讨论如何制造角色差异',
                'stance_label': '谨慎保留',
                'avoid_repeating': [],
                'new_information': '我补充：要把角色目标拆成可检验的判断标准。',
            }

        def participant_content(seat, *, stage_instruction, plan, **_kwargs):
            if '第 2/2 位' in stage_instruction and plan.get('response_target') == '符华':
                return '我认同前一位提出的“判断标准”方向，但还要再加一条硬约束：每轮必须补充新的信息，否则讨论会继续空转。'
            return f"{seat.display_name}：我的初步判断是，{plan['new_information']}这件事应该被优先纳入讨论主线。"

        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=participant_content):
            for _ in range(6):
                group = advance_discussion_group(group)
                group.refresh_from_db()
                if group.state['runtime_status'] == 'blocked':
                    break

        group.refresh_from_db()
        self.assertEqual(group.state['runtime_status'], 'ready')
        self.assertGreaterEqual(group.speeches.count(), 3)

    def test_advancing_group_runs_through_moderated_flow_to_finished(self):
        group = self._create_group(count=2, max_rounds=2)
        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=self._participant_content):
            for _ in range(12):
                group = advance_discussion_group(group)
                if group.status == 'finished':
                    break

        group.refresh_from_db()
        self.assertEqual(group.status, 'finished')
        self.assertEqual(group.phase, 'finished')
        self.assertEqual(group.speeches.filter(audience='public').count(), 7)
        event_types = list(group.events.values_list('event_type', flat=True))
        self.assertIn('moderator_opening', event_types)
        self.assertIn('agenda_setup', event_types)
        self.assertIn('moderator_summary', event_types)
        self.assertIn('consensus_draft', event_types)
        self.assertEqual(group.events.last().event_type, 'game_finished')

    def test_reset_discussion_group_clears_speeches_and_reseeds_runtime(self):
        group = self._create_group()
        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=self._participant_content):
            advance_discussion_group(group)
            advance_discussion_group(group)
            advance_discussion_group(group)

        group = reset_discussion_group(group)
        group.refresh_from_db()

        self.assertEqual(group.status, 'waiting')
        self.assertEqual(group.phase, 'setup')
        self.assertEqual(group.day_number, 0)
        self.assertEqual(group.speeches.count(), 0)
        self.assertEqual(group.events.count(), 1)
        self.assertEqual(group.state['runtime_status'], 'ready')
        self.assertIn('dag_runtime', group.state)
        self.assertEqual(peek_ready_node(group.state['dag_runtime'])['kind'], 'discussion_moderator_opening')

    def test_discussion_api_detail_exposes_plan_and_state(self):
        group = self._create_group()
        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload):
            advance_discussion_group(group)
            advance_discussion_group(group)

        detail_response = self.client.get(f'/api/discussion/groups/{group.id}/')
        self.assertEqual(detail_response.status_code, 200)
        payload = detail_response.json()
        self.assertEqual(payload['group']['topic'], 'AI 角色如何开展高质量群体讨论？')
        self.assertIn('discussion_plan', payload)
        self.assertIn('stance_map', payload)
        self.assertIn('consensus_state', payload)
        self.assertEqual(payload['group']['moderator_participant_name'], '爱莉希雅')
        self.assertTrue(payload['participants'][0]['is_moderator'])
        self.assertEqual(payload['group']['current_stage'], 'agenda_setup')
        self.assertEqual(payload['runtime_status'], 'ready')
        self.assertEqual(len(payload['speeches']), 2)
        self.assertEqual(payload['speeches'][0]['participant_name'], '爱莉希雅')
        self.assertTrue(payload['speeches'][0]['metadata']['is_moderator_speech'])
        self.assertEqual(payload['speeches'][0]['participant_id'], payload['group']['moderator_participant_id'])

    def test_discussion_api_smoke_flow_runs_from_create_to_finish(self):
        with patch('web.discussion_services._pick_round_start_index', return_value=0), \
             patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=self._participant_content):
            create_response = self.client.post(
                '/api/discussion/groups/create/',
                data=json.dumps({
                    'title': 'API 冒烟测试',
                    'topic': '讨论组冒烟测试：怎样让多角色讨论真正跑通？',
                    'character_ids': [character.id for character in self.characters],
                    'max_rounds': 2,
                }),
                content_type='application/json',
            )

            self.assertEqual(create_response.status_code, 201)
            group_id = create_response.json()['group']['id']

            finished_payload = None
            for _ in range(12):
                advance_response = self.client.post(
                    f'/api/discussion/groups/{group_id}/advance/',
                    data=json.dumps({}),
                    content_type='application/json',
                )
                self.assertEqual(
                    advance_response.status_code,
                    200,
                    msg=f'advance failed with payload: {advance_response.json() if hasattr(advance_response, "json") else advance_response.content!r}',
                )
                finished_payload = advance_response.json()
                if finished_payload['group']['status'] == 'finished':
                    break

        self.assertIsNotNone(finished_payload)
        self.assertEqual(finished_payload['group']['status'], 'finished')
        self.assertEqual(finished_payload['group']['phase'], 'finished')
        self.assertEqual(finished_payload['runtime_status'], 'ready')
        self.assertEqual(finished_payload['group']['moderator_participant_name'], '爱莉希雅')
        event_types = [event['event_type'] for event in finished_payload['events']]
        self.assertIn('moderator_opening', event_types)
        self.assertIn('agenda_setup', event_types)
        self.assertIn('moderator_summary', event_types)
        self.assertIn('consensus_draft', event_types)
        self.assertEqual(event_types[-1], 'game_finished')

    def test_discussion_demo_flow_produces_normal_discussion_content(self):
        with patch('web.discussion_services._pick_round_start_index', return_value=0), \
             patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=self._participant_content):
            create_response = self.client.post(
                '/api/discussion/groups/create/',
                data=json.dumps({
                    'title': '讨论 Demo',
                    'topic': '如果要让多角色讨论更像真实圆桌讨论，最该先改哪一层？',
                    'character_ids': [character.id for character in self.characters],
                    'max_rounds': 2,
                }),
                content_type='application/json',
            )

            self.assertEqual(create_response.status_code, 201)
            group_id = create_response.json()['group']['id']

            final_payload = None
            for _ in range(12):
                response = self.client.post(
                    f'/api/discussion/groups/{group_id}/advance/',
                    data=json.dumps({}),
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, 200)
                final_payload = response.json()
                if final_payload['group']['status'] == 'finished':
                    break

        self.assertIsNotNone(final_payload)
        self.assertEqual(final_payload['group']['status'], 'finished')
        self.assertEqual(final_payload['runtime_status'], 'ready')

        speeches = final_payload['speeches']
        self.assertGreaterEqual(len(speeches), 4)
        self.assertTrue(all(len(str(speech['content']).strip()) >= 16 for speech in speeches))
        self.assertTrue(any('角色目标' in str(speech['content']) for speech in speeches))
        self.assertTrue(any('新增信息' in str(speech['content']) or '流程约束' in str(speech['content']) for speech in speeches))

        timeline = {event['event_type']: event for event in final_payload['events']}
        self.assertIn('moderator_opening', timeline)
        self.assertIn('agenda_setup', timeline)
        self.assertIn('moderator_summary', timeline)
        self.assertIn('consensus_draft', timeline)
        self.assertIn('game_finished', timeline)

        self.assertIn('角色讨论已经同质化', timeline['moderator_opening']['content'])
        self.assertIn('议题拆开', timeline['agenda_setup']['content'])
        self.assertTrue(final_payload['consensus_state']['consensus_draft'])
        self.assertIn('目标', final_payload['consensus_state']['consensus_draft'])
        self.assertIn('流程约束', final_payload['consensus_state']['consensus_draft'])

    def test_discussion_api_remove_flow(self):
        group = self._create_group()

        remove_response = self.client.post(f'/api/discussion/groups/{group.id}/remove/')
        self.assertEqual(remove_response.status_code, 200)
        self.assertFalse(WerewolfGame.objects.filter(pk=group.id).exists())

    def test_moderator_payload_without_content_blocks_group(self):
        group = self._create_group()

        def missing_content_payload(seat, *, stage, **_kwargs):
            return {
                'round_goal': '先明确问题边界。',
                'new_focus': '先判断什么叫内容同质化。',
                'agenda_items': ['定义什么叫同质化', '讨论如何制造角色差异'],
                'resolved_points': [],
                'open_questions': ['不同角色应该在哪一层体现差异？'],
                'consensus_draft': '',
                'route': '',
            }

        with patch('web.discussion_services._generate_moderator_payload', side_effect=missing_content_payload):
            group = advance_discussion_group(group)

        group.refresh_from_db()
        self.assertEqual(group.state['runtime_status'], 'blocked')
        self.assertEqual(group.state['last_failure']['failure_code'], 'invalid_moderator_plan')
        self.assertEqual(group.state['last_failure']['failure_reason'], '主持发言缺少 content。')

    def test_moderator_payload_without_agenda_items_blocks_group(self):
        group = self._create_group()

        def missing_agenda_payload(seat, *, stage, **_kwargs):
            return {
                'content': f'{seat.display_name}：这轮我先把讨论重点定一下。',
                'round_goal': '先明确问题边界。',
                'new_focus': '先判断什么叫内容同质化。',
                'resolved_points': [],
                'open_questions': ['不同角色应该在哪一层体现差异？'],
                'consensus_draft': '',
                'route': '',
            }

        with patch('web.discussion_services._generate_moderator_payload', side_effect=missing_agenda_payload):
            group = advance_discussion_group(group)

        group.refresh_from_db()
        self.assertEqual(group.state['runtime_status'], 'blocked')
        self.assertEqual(group.state['last_failure']['failure_code'], 'invalid_moderator_plan')
        self.assertEqual(group.state['last_failure']['failure_reason'], '主持发言缺少 agenda_items。')

    def test_moderator_string_fields_are_normalized_without_character_splitting(self):
        group = self._create_group()

        def string_field_payload(seat, *, stage, **_kwargs):
            content = f'{seat.display_name}：我先把讨论范围定住，先看什么叫内容同质化。'
            if stage == 'agenda_setup':
                content = f'{seat.display_name}：接下来我把议题拆开，请大家分别回应定义标准和角色差异这两个点。'
            return {
                'content': content,
                'round_goal': '先明确问题边界。',
                'new_focus': '先判断什么叫内容同质化。',
                'agenda_items': '定义什么叫同质化',
                'resolved_points': '',
                'open_questions': '不同角色应该在哪一层体现差异？',
                'consensus_draft': '',
                'route': '',
            }

        with patch('web.discussion_services._generate_moderator_payload', side_effect=string_field_payload):
            advance_discussion_group(group)
            advance_discussion_group(group)

        group.refresh_from_db()
        plan = group.state['discussion_plan']
        consensus_state = group.state['consensus_state']
        self.assertEqual(plan['agenda_items'], ['定义什么叫同质化'])
        self.assertEqual(consensus_state['open_questions'], ['不同角色应该在哪一层体现差异？'])

    def test_retry_failed_node_via_advance_recovers_group(self):
        group = self._create_group(count=3, max_rounds=2)
        with patch('web.discussion_services._generate_moderator_payload', side_effect=self._moderator_payload), \
             patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=[
                 '爱莉希雅认为，关于角色差异，首先该区分角色目标，而不是单纯语气。',
                 '爱莉希雅认为，关于角色差异，首先该区分角色目标，而不是单纯语气。',
             ]):
            advance_discussion_group(group)
            advance_discussion_group(group)
            advance_discussion_group(group)
            failure_response = self.client.post(f'/api/discussion/groups/{group.id}/advance/', data=json.dumps({}), content_type='application/json')

        self.assertEqual(failure_response.status_code, 400)
        group.refresh_from_db()
        self.assertEqual(group.state['runtime_status'], 'blocked')

        with patch('web.discussion_services._plan_participant_turn', side_effect=self._participant_plan), \
             patch('web.discussion_services.generate_discussion_reply', side_effect=self._participant_content):
            retry_response = self.client.post(
                f'/api/discussion/groups/{group.id}/advance/',
                data=json.dumps({'retry_failed_node': True}),
                content_type='application/json',
            )

        self.assertEqual(retry_response.status_code, 200)
        group.refresh_from_db()
        self.assertEqual(group.state['runtime_status'], 'ready')


class DiscussionTransactionTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.user = get_or_create_local_operator_user()
        self.characters = [
            Character.objects.create(user=self.user, name='爱莉希雅', profile='偏乐观，喜欢抛出开放问题。'),
            Character.objects.create(user=self.user, name='符华', profile='偏理性，习惯拆解问题。'),
        ]

    def test_model_generation_runs_outside_atomic_transaction(self):
        with patch('web.discussion_services._pick_round_start_index', return_value=0):
            group = create_discussion_group(
                title='事务测试',
                topic='测试讨论推进时是否持有长事务',
                character_ids=[character.id for character in self.characters],
                max_rounds=2,
            )

        def assert_not_atomic(*_args, **_kwargs):
            self.assertFalse(connection.in_atomic_block)
            return {
                'content': '爱莉希雅：我们先把真实感拆成结构约束、角色目标和回应质量三个层次。',
                'round_goal': '先明确问题边界。',
                'new_focus': '优先讨论结构约束和角色目标的关系。',
                'agenda_items': ['定义真实感', '区分角色目标与流程约束'],
                'resolved_points': [],
                'open_questions': ['先改结构还是先改角色目标？'],
                'consensus_draft': '',
                'route': '',
            }

        with patch('web.discussion_services._generate_moderator_payload', side_effect=assert_not_atomic):
            advance_discussion_group(group)
        group.refresh_from_db()
        self.assertEqual(group.state['runtime_status'], 'ready')
        self.assertEqual(group.events.count(), 2)


class DiscussionGuardrailTests(TestCase):
    def test_leakage_guardrail_does_not_block_normal_system_discussion(self):
        text = '这不是简单的系统设计问题，而是一个风险结构和责任分配的问题。'
        self.assertFalse(_contains_off_topic_or_leakage(text))

    def test_leakage_guardrail_blocks_prompt_and_system_meta_talk(self):
        self.assertTrue(_contains_off_topic_or_leakage('作为AI，我需要遵循系统要求来回答。'))
