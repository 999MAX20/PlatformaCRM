from rest_framework import serializers

from apps.ai_core.models import AIJob, AIToolCallLog, AIRequestLog, AgentProfile, ApprovalRequest, BusinessKnowledgeItem
from apps.businesses.models import Business
from apps.bots.models import BotConversation
from apps.integrations.sanitization import sanitize_config, sanitize_error_text


class AIRequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRequestLog
        fields = "__all__"
        read_only_fields = [field.name for field in AIRequestLog._meta.fields]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["input_json"] = sanitize_config(data.get("input_json") or {})
        data["output_text"] = sanitize_error_text(data.get("output_text"))
        return data


class BusinessKnowledgeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessKnowledgeItem
        fields = ["id", "business", "bot", "title", "content", "category", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        business = attrs.get("business", getattr(self.instance, "business", None))
        bot = attrs.get("bot", getattr(self.instance, "bot", None))
        if bot and (bot.business_id != business.pk or bot.is_deleted):
            raise serializers.ValidationError({"bot": "Agent is unavailable for this business."})
        if self.instance and (business != self.instance.business or bot != self.instance.bot):
            raise serializers.ValidationError("Knowledge ownership cannot change.")
        return attrs

    def create(self, validated_data):
        from apps.ai_core.knowledge import save_knowledge
        return save_knowledge(actor=self.context["request"].user, data=validated_data)

    def update(self, instance, validated_data):
        from apps.ai_core.knowledge import save_knowledge
        return save_knowledge(actor=self.context["request"].user, data=validated_data, item=instance)


class KnowledgeConnectionSerializer(serializers.Serializer):
    agent = serializers.IntegerField(min_value=1)
    connected = serializers.BooleanField()


class AgentProfileSerializer(serializers.ModelSerializer):
    bot_name = serializers.CharField(source="bot.name", read_only=True)

    class Meta:
        model = AgentProfile
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        business = attrs.get("business") or getattr(self.instance, "business", None)
        bot = attrs.get("bot") if "bot" in attrs else getattr(self.instance, "bot", None)
        if business and bot and bot.business_id != business.id:
            raise serializers.ValidationError("Bot must belong to the selected business.")
        if bot and bot.is_deleted:
            raise serializers.ValidationError("This AI agent has been deleted.")
        for field, key in (("rules_json", "items"), ("escalation_rules_json", "items"), ("allowed_tools_json", "tools")):
            if field not in attrs:
                continue
            value = attrs[field]
            if field != "allowed_tools_json" and isinstance(value, list):
                value = {key: value}
                attrs[field] = value
            if not isinstance(value, dict) or (key in value and (not isinstance(value[key], list) or any(not isinstance(item, str) for item in value[key]))):
                raise serializers.ValidationError({field: "Expected an object containing a list of strings."})
        rules = attrs.get("rules_json", getattr(self.instance, "rules_json", {}))
        if isinstance(rules, dict) and "scenario" in rules:
            from apps.ai_core.workflows import SCENARIOS, SOURCES
            if rules["scenario"] not in SCENARIOS or bot is not None:
                raise serializers.ValidationError({"rules_json": "Internal scenarios cannot be attached to a messenger bot."})
            sources = rules.get("sources", sorted(SOURCES))
            if not isinstance(sources, list) or any(not isinstance(source, str) or source not in SOURCES for source in sources):
                raise serializers.ValidationError({"rules_json": "Unsupported data source."})
            from apps.ai_core.tool_registry import TOOLS
            tools = attrs.get("allowed_tools_json", getattr(self.instance, "allowed_tools_json", {})).get("tools", [])
            if any(tool not in TOOLS for tool in tools) or (rules["scenario"] == "analyst" and tools):
                raise serializers.ValidationError({"allowed_tools_json": "Unsupported scenario capability."})
        if bot and bot.scenario == "crm":
            from apps.ai_core.workflows import SOURCES
            from apps.ai_core.tool_registry import TOOLS
            if not isinstance(rules, dict) or "scenario" in rules:
                raise serializers.ValidationError({"rules_json": "Use the CRM agent's unified settings."})
            sources = rules.get("sources", sorted(SOURCES))
            if not isinstance(sources, list) or any(not isinstance(item, str) or item not in SOURCES for item in sources):
                raise serializers.ValidationError({"rules_json": "Unsupported data source."})
            if "analyst_enabled" in rules and not isinstance(rules["analyst_enabled"], bool):
                raise serializers.ValidationError({"rules_json": "Analyst enabled must be boolean."})
            tools = attrs.get("allowed_tools_json", getattr(self.instance, "allowed_tools_json", {})).get("tools", [])
            if any(tool not in TOOLS for tool in tools):
                raise serializers.ValidationError({"allowed_tools_json": "Unsupported CRM capability."})
        if "language" in attrs and attrs["language"] not in {"ru", "kk", "en"}:
            raise serializers.ValidationError({"language": "Unsupported agent language."})
        if bot and self.context.get("request") and (bot.settings_json.get("auto_crm_pipeline") or {}).get("creation_policy") == "automatic":
            from apps.bots.automation_policy import authorize_configuration
            tools = attrs.get("allowed_tools_json", getattr(self.instance, "allowed_tools_json", {})).get("tools", [])
            authorize_configuration(bot, bot.settings_json, tools, self.context["request"].user)
        return attrs


class AIAssistantChatSerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())
    message = serializers.CharField(required=True, allow_blank=False)
    prompt_type = serializers.ChoiceField(choices=["crm_assistant", "daily_summary"], required=False, default="crm_assistant")
    idempotency_key = serializers.CharField(required=False, max_length=160)


class AIJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIJob
        fields = ["id", "business", "status", "attempts", "max_attempts", "next_retry_at", "result_json", "error", "created_at", "completed_at"]
        read_only_fields = [field.name for field in AIJob._meta.fields]


class AIAssistantStatusSerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())


class AIAnalystBriefSerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())
    limit = serializers.IntegerField(required=False, min_value=1, max_value=50, default=24)


class AIOwnerDailyBriefSerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=8)


class AIToolCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIToolCallLog
        fields = "__all__"
        read_only_fields = ["created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["input_json"] = sanitize_config(data.get("input_json") or {})
        data["output_json"] = sanitize_config(data.get("output_json") or {})
        data["error"] = sanitize_error_text(data.get("error"))
        return data


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)
    approved_by_email = serializers.EmailField(source="approved_by.email", read_only=True)
    rejected_by_email = serializers.EmailField(source="rejected_by.email", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "requested_by",
            "status",
            "approved_by",
            "approved_at",
            "rejected_by",
            "rejected_at",
        ]

    def validate(self, attrs):
        business = attrs.get("business") or getattr(self.instance, "business", None)
        ai_request_log = attrs.get("ai_request_log") if "ai_request_log" in attrs else getattr(self.instance, "ai_request_log", None)
        ai_tool_call_log = attrs.get("ai_tool_call_log") if "ai_tool_call_log" in attrs else getattr(self.instance, "ai_tool_call_log", None)
        if ai_request_log and business and ai_request_log.business_id != business.id:
            raise serializers.ValidationError({"ai_request_log": "AI request log must belong to the selected business."})
        if ai_tool_call_log and business and ai_tool_call_log.business_id != business.id:
            raise serializers.ValidationError({"ai_tool_call_log": "AI tool call must belong to the selected business."})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["payload"] = sanitize_config(data.get("payload") or {})
        return data


class AIToolSuggestSerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())
    conversation = serializers.PrimaryKeyRelatedField(queryset=BotConversation.objects.all(), required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True)
    tool_name = serializers.ChoiceField(choices=["crm_create", "crm_update", "crm_archive", "crm_restore", "crm_transition"], required=False)
    arguments = serializers.DictField(required=False)

    def validate(self, attrs):
        business = attrs["business"]
        conversation = attrs.get("conversation")
        if conversation and conversation.business_id != business.id:
            raise serializers.ValidationError("Conversation must belong to the selected business.")
        if ("tool_name" in attrs) != ("arguments" in attrs):
            raise serializers.ValidationError("Command and arguments must be provided together.")
        return attrs
