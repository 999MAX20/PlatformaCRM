from apps.conversations.models import Conversation, Message, QuickReplyTemplate
from apps.conversations.serializers import ConversationSerializer, MessageSerializer, QuickReplyTemplateSerializer
from apps.core.viewsets import TenantModelViewSet
from apps.businesses.access import Actions, Resources, assert_can


class ConversationViewSet(TenantModelViewSet):
    queryset = Conversation.objects.select_related("business", "client")
    serializer_class = ConversationSerializer


class MessageViewSet(TenantModelViewSet):
    queryset = Message.objects.select_related("conversation", "conversation__business")
    serializer_class = MessageSerializer
    business_lookup = "conversation__business"


class QuickReplyTemplateViewSet(TenantModelViewSet):
    queryset = QuickReplyTemplate.objects.select_related("business")
    serializer_class = QuickReplyTemplateSerializer
    access_resource = "conversations"
    action_permission_map = {
        **TenantModelViewSet.action_permission_map,
        "create": Actions.MANAGE,
        "update": Actions.MANAGE,
        "partial_update": Actions.MANAGE,
        "destroy": Actions.MANAGE,
    }

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        assert_can(request.user, instance.business, Resources.CONVERSATIONS, Actions.MANAGE, obj=instance)
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        if "business" in self.request.query_params:
            from rest_framework.fields import IntegerField

            queryset = queryset.filter(business_id=IntegerField(min_value=1).run_validation(self.request.query_params["business"]))
        channel = self.request.query_params.get("channel")
        active = self.request.query_params.get("is_active")
        search = (self.request.query_params.get("q") or "").strip()
        if channel:
            queryset = queryset.filter(channel__in=["all", channel])
        if active in {"true", "false"}:
            queryset = queryset.filter(is_active=active == "true")
        if search:
            queryset = queryset.filter(title__icontains=search) | queryset.filter(text__icontains=search)
        return queryset.distinct()
