"""Explicit OS entitlement provisioning; independent of staff/master grants."""
from .network_policy import NetworkCommand, arguments, integer
from apps.core.network_oob import change_operator


class Command(NetworkCommand):
    help = 'Explicitly grant or revoke a deployment network operator entitlement.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['grant', 'revoke'])
        arguments(parser)
        parser.add_argument('--organisation', required=True)
        parser.add_argument('--user-id', required=True, type=integer)
        parser.add_argument('--expected-version', required=True, type=integer)
        parser.add_argument('--expected-revision', required=True, type=integer)

    def execute_operation(self, context, options):
        return change_operator(context, options['organisation'], options['user_id'], options['expected_version'], options['expected_revision'], options['action'])
