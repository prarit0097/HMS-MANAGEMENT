"""Local audited network policy operations; no arbitrary input policy execution."""
import argparse
import json
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError
from apps.core.network_authority import NetworkError
from apps.core.network_snapshot import NetworkStateUnavailable
from apps.core.network_oob import OutOfBandContext, inspect_policy, bind_owner, recover_policy, transfer_owner
from apps.core.network_access import reconcile_expired_policy


def integer(value):
    if not value.isascii() or not value.isdecimal() or len(value) > 16 or int(value) > 9007199254740991:
        raise argparse.ArgumentTypeError('Use a bounded whole number.')
    return int(value)


def arguments(parser):
    parser.add_argument('--os-actor', required=True)
    parser.add_argument('--reason', required=True)


class NetworkCommand(BaseCommand):
    def create_parser(self, *args, **kwargs):
        parser = super().create_parser(*args, **kwargs)
        def error(message):
            raise CommandError('Invalid command arguments.', returncode=2)
        parser.error = error
        return parser

    def execute_operation(self, context, options):
        raise NotImplementedError

    def handle(self, *args, **options):
        try:
            context = OutOfBandContext(options['os_actor'], options['reason'])
            result = self.execute_operation(context, options)
            self.stdout.write(json.dumps(result, sort_keys=True))
        except NetworkError as exc:
            raise CommandError(str(exc.detail), returncode=3 if exc.status_code == 503 else 2) from None
        except (NetworkStateUnavailable, DatabaseError, ObjectDoesNotExist):
            raise CommandError('Network settings are unavailable; repair the database or configuration through the authorised OS process.', returncode=3) from None


class Command(NetworkCommand):
    help = 'Inspect, bind, reconcile or explicitly recover deployment network settings.'

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest='action', required=True)
        for action in ('inspect', 'bind-owner', 'reconcile', 'recover', 'transfer-owner'):
            sub = actions.add_parser(action)
            # Subparser errors must retain the command-specific invalid-input exit code.
            sub.error = lambda message: (_ for _ in ()).throw(CommandError('Invalid command arguments.', returncode=2))
            arguments(sub)
            if action in ('bind-owner', 'recover', 'transfer-owner'):
                sub.add_argument('--expected-revision', required=True, type=integer)
            if action == 'bind-owner':
                sub.add_argument('--organisation', required=True)
            if action == 'recover':
                sub.add_argument('--change', required=True)
                sub.add_argument('--snapshot', required=True, choices=['candidate', 'fallback'])
            if action == 'transfer-owner':
                sub.add_argument('--from', dest='previous_owner', required=True)
                sub.add_argument('--to', dest='new_owner', required=True)
            if action in ('recover', 'transfer-owner'):
                sub.add_argument('--apply', action='store_true')

    def execute_operation(self, context, options):
        action = options['action']
        if action == 'inspect':
            return inspect_policy(context)
        if action == 'bind-owner':
            return bind_owner(context, options['organisation'], options['expected_revision'])
        if action == 'reconcile':
            return reconcile_expired_policy(context)
        if action == 'recover':
            return recover_policy(context, options['change'], options['snapshot'], options['expected_revision'], apply=options['apply'])
        return transfer_owner(context, options['previous_owner'], options['new_owner'], options['expected_revision'], apply=options['apply'])
