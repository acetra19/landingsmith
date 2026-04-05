"""
State machine governing valid lead transitions through the pipeline.
Each transition maps (current_status) → [allowed_next_statuses].
"""

from database.models import LeadStatus

TRANSITIONS: dict[LeadStatus, list[LeadStatus]] = {
    LeadStatus.DISCOVERED: [
        LeadStatus.VERIFIED,
        LeadStatus.REJECTED,
    ],
    LeadStatus.VERIFIED: [
        LeadStatus.WEBSITE_BUILDING,
        LeadStatus.REJECTED,
    ],
    LeadStatus.WEBSITE_BUILDING: [
        LeadStatus.WEBSITE_READY,
        LeadStatus.REJECTED,
    ],
    LeadStatus.WEBSITE_READY: [
        LeadStatus.DEPLOYED,
        LeadStatus.WEBSITE_BUILDING,  # rebuild
        LeadStatus.REJECTED,
    ],
    LeadStatus.DEPLOYED: [
        LeadStatus.OUTREACH_SENT,
        LeadStatus.REJECTED,
    ],
    LeadStatus.OUTREACH_SENT: [
        LeadStatus.FOLLOW_UP_1,
        LeadStatus.RESPONDED,
        LeadStatus.BOUNCED,
        LeadStatus.UNSUBSCRIBED,
    ],
    LeadStatus.FOLLOW_UP_1: [
        LeadStatus.FOLLOW_UP_2,
        LeadStatus.RESPONDED,
        LeadStatus.BOUNCED,
        LeadStatus.UNSUBSCRIBED,
    ],
    LeadStatus.FOLLOW_UP_2: [
        LeadStatus.RESPONDED,
        LeadStatus.BOUNCED,
        LeadStatus.UNSUBSCRIBED,
        LeadStatus.REJECTED,
    ],
    LeadStatus.RESPONDED: [
        LeadStatus.INTERESTED,
        LeadStatus.REJECTED,
    ],
    LeadStatus.INTERESTED: [
        LeadStatus.CONVERTED,
        LeadStatus.REJECTED,
    ],
    # Terminal states — no transitions out
    LeadStatus.CONVERTED: [],
    LeadStatus.UNSUBSCRIBED: [],
    LeadStatus.BOUNCED: [],
    LeadStatus.REJECTED: [],
}


class LeadStateMachine:
    @staticmethod
    def can_transition(current: LeadStatus, target: LeadStatus) -> bool:
        allowed = TRANSITIONS.get(current, [])
        return target in allowed

    @staticmethod
    def get_allowed_transitions(current: LeadStatus) -> list[LeadStatus]:
        return TRANSITIONS.get(current, [])

    @staticmethod
    def is_terminal(status: LeadStatus) -> bool:
        return len(TRANSITIONS.get(status, [])) == 0

    @staticmethod
    def transition(current: LeadStatus, target: LeadStatus) -> LeadStatus:
        if not LeadStateMachine.can_transition(current, target):
            raise InvalidTransitionError(
                f"Cannot transition from {current.value} to {target.value}. "
                f"Allowed: {[s.value for s in LeadStateMachine.get_allowed_transitions(current)]}"
            )
        return target


class InvalidTransitionError(Exception):
    pass
