"""Pydantic schemas for data serialization and API request/response validation."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------------------------------------
# Participant Schemas
# -------------------------------------------------------------
class ParticipantBase(BaseModel):
    name: str
    avatar_color: str = "#4f46e5"
    speaking_time: float = 0.0
    speaking_percentage: float = 0.0
    turn_count: int = 0
    avg_turn_length: float = 0.0
    median_turn_length: float = 0.0
    longest_turn: float = 0.0
    shortest_turn: float = 0.0
    turn_std_dev: float = 0.0
    interruptions_made: int = 0
    interruptions_received: int = 0
    responses_count: int = 0
    ideas_introduced: int = 0
    actions_assigned: int = 0
    employee_id: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    responsibilities: Optional[str] = None


class ParticipantSchema(ParticipantBase):
    id: int
    meeting_id: int
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Transcript Segment Schemas
# -------------------------------------------------------------
class TranscriptSegmentSchema(BaseModel):
    id: int
    meeting_id: int
    turn_number: int
    speaker_name: str
    start_time: float
    end_time: float
    text: str
    topic_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Action Item Schemas
# -------------------------------------------------------------
class ActionItemBase(BaseModel):
    task: str
    owner: str = "Unknown"
    due_date: str = "Unknown"
    priority: str = "Medium"
    confidence: float = 0.85
    status: str = "Detected"
    evidence: Optional[str] = None
    external_reference: Optional[str] = None


class ActionItemSchema(ActionItemBase):
    id: int
    meeting_id: int
    source_segment_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class ActionItemUpdateSchema(BaseModel):
    task: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None  # "Detected", "Confirmed", "Assigned", "In Progress", "Completed", "Rejected"


# -------------------------------------------------------------
# Idea Schemas
# -------------------------------------------------------------
class IdeaSchema(BaseModel):
    id: int
    meeting_id: int
    speaker: str
    text: str
    timestamp: float
    confidence: float
    lifecycle_stage: str
    source_segment_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class IdeaRelationSchema(BaseModel):
    id: int
    meeting_id: int
    idea_a_id: int
    idea_b_id: int
    similarity_score: float
    time_difference: float
    relation_type: str
    details: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Decision Schemas
# -------------------------------------------------------------
class DecisionSchema(BaseModel):
    id: int
    meeting_id: int
    text: str
    timestamp: float
    confidence: float
    participants_involved: Optional[str] = None
    related_idea_id: Optional[int] = None
    source_segment_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Topic Schemas
# -------------------------------------------------------------
class TopicSchema(BaseModel):
    id: int
    meeting_id: int
    name: str
    start_time: float
    end_time: float
    status: str
    evidence: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Interaction Schemas
# -------------------------------------------------------------
class InteractionSchema(BaseModel):
    id: int
    meeting_id: int
    speaker_a: str
    speaker_b: str
    interaction_type: str
    timestamp: float
    confidence: float
    evidence: Optional[str] = None
    source_segment_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Meeting Schemas
# -------------------------------------------------------------
class MeetingSummarySchema(BaseModel):
    id: int
    title: str
    date: Optional[str] = None
    duration: float
    transcript_filename: Optional[str] = None
    created_at: datetime
    status: str
    participant_count: int = 0
    action_item_count: int = 0
    decision_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class MeetingDetailSchema(BaseModel):
    id: int
    title: str
    date: Optional[str] = None
    duration: float
    transcript_filename: Optional[str] = None
    created_at: datetime
    status: str
    summary: Optional[str] = None
    participants: List[ParticipantSchema] = []
    action_items: List[ActionItemSchema] = []
    ideas: List[IdeaSchema] = []
    decisions: List[DecisionSchema] = []
    topics: List[TopicSchema] = []
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Integration Dispatch Schemas
# -------------------------------------------------------------
class IntegrationDispatchSchema(BaseModel):
    meeting_id: int
    action_item_ids: Optional[List[int]] = None
    channel_or_list: Optional[str] = None


# -------------------------------------------------------------
# Feature 1: Attendance Schemas
# -------------------------------------------------------------
class AttendanceRecordSchema(BaseModel):
    id: Optional[int] = None
    meeting_id: int
    participant_id: Optional[int] = None
    employee_name: str
    employee_id: Optional[str] = None
    role: Optional[str] = None
    join_time: float = 0.0
    join_time_display: str = "00:00"
    leave_time: float = 0.0
    leave_time_display: str = "00:00"
    duration: float = 0.0
    duration_display: str = "0 min"
    meeting_duration: float = 0.0
    meeting_duration_display: str = "0 min"
    attendance_percentage: float = 0.0
    late_duration: float = 0.0
    late_display: str = "0 min"
    early_leave_duration: float = 0.0
    early_leave_display: str = "0 min"
    first_transcript_time: Optional[float] = None
    first_transcript_display: Optional[str] = None
    last_transcript_time: Optional[float] = None
    last_transcript_display: Optional[str] = None
    is_verified: bool = False
    verification_label: str = "Estimated from transcript"  # "Verified attendance" vs "Estimated from transcript"
    status: str = "On time"  # "On time", "Late", "Left early", "Late & Left early", "Partial attendance"
    model_config = ConfigDict(from_attributes=True)


class AttendanceSummarySchema(BaseModel):
    meeting_id: int
    meeting_duration: float
    total_participants: int
    verified_count: int
    estimated_count: int
    average_attendance_percentage: float
    late_arrivals_count: int
    early_departures_count: int
    records: List[AttendanceRecordSchema] = []


class AttendanceUpdateSchema(BaseModel):
    join_time: Optional[float] = None
    leave_time: Optional[float] = None
    employee_id: Optional[str] = None
    role: Optional[str] = None
    is_verified: Optional[bool] = True


class AttendanceCreateSchema(BaseModel):
    employee_name: str
    employee_id: Optional[str] = None
    role: Optional[str] = None
    join_time: float = 0.0
    leave_time: float = 0.0
    is_verified: bool = True


# -------------------------------------------------------------
# Feature 2 & 3: Meeting Plan & Pre-Meeting Schemas
# -------------------------------------------------------------
class ParticipantPlanInput(BaseModel):
    name: str
    role: Optional[str] = None
    department: Optional[str] = None
    responsibilities: Optional[str] = None


class MeetingPlanGenerateRequest(BaseModel):
    topic: str
    objective: Optional[str] = None
    duration_minutes: int = 45
    department: Optional[str] = None
    meeting_type: str = "Sprint Planning"
    industry_context: Optional[str] = None
    participants: List[ParticipantPlanInput] = []


class AgendaItemSchema(BaseModel):
    time_window: str
    title: str
    lead: str
    objective: str


class RoleExpectationSchema(BaseModel):
    name: str
    role: str
    department: Optional[str] = None
    responsibilities: Optional[str] = None
    expected_topics: List[str] = []


class MeetingPlanResponse(BaseModel):
    id: Optional[int] = None
    meeting_id: Optional[int] = None
    topic: str
    objective: Optional[str] = None
    duration_minutes: int = 45
    department: Optional[str] = None
    meeting_type: str = "Sprint Planning"
    industry_context: Optional[str] = None
    suggested_agenda: List[AgendaItemSchema] = []
    expected_topics: List[str] = []
    expected_questions: List[str] = []
    expected_decisions: List[str] = []
    expected_action_areas: List[str] = []
    role_expectations: List[RoleExpectationSchema] = []
    disclaimer: str = "AI-generated expected discussion (Predictions / planning suggestions, NOT actual meeting facts)"
    is_ai_generated: bool = True


class MeetingPlanSaveRequest(BaseModel):
    meeting_id: Optional[int] = None
    topic: str
    objective: Optional[str] = None
    duration_minutes: int = 45
    department: Optional[str] = None
    meeting_type: str = "Sprint Planning"
    industry_context: Optional[str] = None
    suggested_agenda: List[Dict[str, Any]] = []
    expected_topics: List[str] = []
    expected_questions: List[str] = []
    expected_decisions: List[str] = []
    expected_action_areas: List[str] = []
    role_expectations: List[Dict[str, Any]] = []


# -------------------------------------------------------------
# Feature 3: Role-Based Contribution Schemas
# -------------------------------------------------------------
class ParticipantContributionSchema(BaseModel):
    name: str
    role: str
    department: Optional[str] = None
    responsibilities: Optional[str] = None
    expected_topics: List[str] = []
    covered_topics: List[str] = []
    coverage_percentage: float = 0.0
    speaking_time: float = 0.0
    speaking_time_display: str = "0m 00s"
    speaking_percentage: float = 0.0
    ideas_contributed: int = 0
    questions_asked: int = 0
    action_items_assigned: int = 0
    decisions_contributed: int = 0
    neutral_observation: str = "Observed participation based on dialogue transcript cadence."


class RoleContributionsResponse(BaseModel):
    meeting_id: int
    contributions: List[ParticipantContributionSchema] = []
    neutral_governance_notice: str = "Evaluation is conducted under scientific neutrality without competence judgements."


# -------------------------------------------------------------
# Feature 4: Topic Coverage Schemas
# -------------------------------------------------------------
class TopicCoverageItemSchema(BaseModel):
    expected_topic: str
    status: str  # "Covered", "Partially Covered", "Not Discussed"
    similarity_score: float = 0.0
    matched_transcript_topic: Optional[str] = None
    duration_seconds: float = 0.0
    duration_display: str = "0s"
    evidence: Optional[str] = None
    decisions_count: int = 0
    action_items_count: int = 0


class TopicCoverageResponse(BaseModel):
    meeting_id: int
    total_expected: int
    covered_count: int
    partially_covered_count: int
    not_discussed_count: int
    coverage_percentage: float
    coverage_bar: str
    explainable_reason: str
    topics: List[TopicCoverageItemSchema] = []
    missing_topics: List[str] = []
    partially_covered_topics: List[str] = []
    fully_covered_topics: List[str] = []


# -------------------------------------------------------------
# Feature 5: Agenda Drift Schemas
# -------------------------------------------------------------
class AgendaDriftItemSchema(BaseModel):
    id: int
    meeting_id: int
    start_time: float
    start_time_display: str
    end_time: float
    end_time_display: str
    duration: float
    duration_display: str
    percentage: float
    detected_topic: str
    expected_topic: str
    category: str  # Minor Drift, Moderate Drift, Significant Drift
    confidence: float
    excerpt: Optional[str] = None
    feedback_status: str = "unreviewed"  # "unreviewed", "confirmed_drift", "not_drift"
    model_config = ConfigDict(from_attributes=True)


class AgendaDriftTimelineBlock(BaseModel):
    start_time: float
    end_time: float
    start_display: str
    end_display: str
    duration: float
    is_drift: bool
    status_label: str  # "On Agenda" vs "Potential Drift"
    topic: str
    category: Optional[str] = None
    confidence: Optional[float] = None
    drift_id: Optional[int] = None


class AgendaDriftResponse(BaseModel):
    meeting_id: int
    total_meeting_duration: float
    drift_detected: bool
    total_drift_incidents: int
    total_drift_duration: float
    total_drift_percentage: float
    drifts: List[AgendaDriftItemSchema] = []
    timeline: List[AgendaDriftTimelineBlock] = []
    neutral_notice: str = "Neutral observation: Drift detection identifies semantic shifts from planned topics."


class AgendaDriftFeedbackRequest(BaseModel):
    feedback: str  # "confirmed_drift" or "not_drift"


# -------------------------------------------------------------
# Feature 6: Silent Participant / Participation Gap Schemas
# -------------------------------------------------------------
class ParticipationGapItemSchema(BaseModel):
    participant_name: str
    role: Optional[str] = "Participant"
    speaking_time: float
    speaking_time_display: str
    speaking_share_percentage: float
    turn_count: int
    questions_count: int
    ideas_count: int
    responses_count: int
    actions_assigned: int
    topic_participation_count: int
    attendance_duration: float
    attendance_display: str
    attendance_percentage: float
    detection_label: str = "Low observed participation"
    neutral_explanation: str
    facilitation_suggestion: str


class ParticipationGapsResponse(BaseModel):
    meeting_id: int
    average_speaking_share: float
    threshold_percentage: float
    total_participants: int
    gaps_count: int
    gaps: List[ParticipationGapItemSchema] = []
    all_participants_overview: List[Dict[str, Any]] = []
    neutral_governance_notice: str = "Participation gaps reflect observed dialogue cadence and should not be used as performance ratings."


# -------------------------------------------------------------
# Feature 7: Recurring Topics Schemas
# -------------------------------------------------------------
class RecurringTopicOccurrenceSchema(BaseModel):
    meeting_id: int
    meeting_title: str
    meeting_date: Optional[str] = None
    topic_title: str
    timestamp: float = 0.0
    timestamp_display: str = "00:00"
    status: str = "Unresolved"
    decision_text: Optional[str] = None
    excerpt: Optional[str] = None
    speakers: Optional[str] = None


class RecurringTopicItemSchema(BaseModel):
    id: Optional[int] = None
    topic: str
    occurrences_count: int
    first_detected_meeting: Dict[str, Any]
    last_detected_meeting: Dict[str, Any]
    status: str  # "Resolved", "Unresolved", "Recurring"
    latest_decision: Optional[str] = None
    historical_timeline: List[Dict[str, Any]] = []
    occurrences: List[RecurringTopicOccurrenceSchema] = []


class RecurringTopicsResponse(BaseModel):
    total_recurring_topics: int
    unresolved_count: int
    resolved_count: int
    topics: List[RecurringTopicItemSchema] = []

