/**
 * API Client for Meeting Intelligence & Social Dynamics Analyzer
 */

const API_BASE = '';

const API = {
  async getMeetings() {
    const res = await fetch(`${API_BASE}/api/meetings`);
    return await res.json();
  },

  async getMeeting(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}`);
    return await res.json();
  },

  async getTranscript(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/transcript`);
    return await res.json();
  },

  async getParticipants(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/participants`);
    return await res.json();
  },

  async getActionItems(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/action-items`);
    return await res.json();
  },

  async acceptActionItem(itemId) {
    const res = await fetch(`${API_BASE}/api/action-items/${itemId}/accept`, { method: 'POST' });
    return await res.json();
  },

  async rejectActionItem(itemId) {
    const res = await fetch(`${API_BASE}/api/action-items/${itemId}/reject`, { method: 'POST' });
    return await res.json();
  },

  async updateActionItem(itemId, payload) {
    const res = await fetch(`${API_BASE}/api/action-items/${itemId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  async getIdeas(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/ideas`);
    return await res.json();
  },

  async getIdeaJourneys(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/idea-journeys`);
    return await res.json();
  },

  async getAttributionShifts(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/attribution-shifts`);
    return await res.json();
  },

  async getDecisions(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/decisions`);
    return await res.json();
  },

  async getTopics(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/topics`);
    return await res.json();
  },

  async getSocialGraph(id, filterType = 'all') {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/social-graph?filter_type=${encodeURIComponent(filterType)}`);
    return await res.json();
  },

  async getReplayState(id, t = 0) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/replay?t=${t}`);
    return await res.json();
  },

  async getTemporalShifts(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/temporal-shifts`);
    return await res.json();
  },

  async getHealthTimeline(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/health-timeline`);
    return await res.json();
  },

  async seedDemo() {
    const res = await fetch(`${API_BASE}/api/meetings/seed-demo`, { method: 'POST' });
    return await res.json();
  },

  async uploadMeeting(formData) {
    const res = await fetch(`${API_BASE}/api/meetings/upload`, {
      method: 'POST',
      body: formData
    });
    return await res.json();
  },

  async dispatchIntegration(platform, payload) {
    const res = await fetch(`${API_BASE}/api/integrations/${platform}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  async compareMeetings(ids) {
    const res = await fetch(`${API_BASE}/api/meetings/compare/metrics?ids=${encodeURIComponent(ids)}`);
    return await res.json();
  },

  // Feature 1: Attendance
  async getAttendance(id) {
    const res = await fetch(`${API_BASE}/api/meetings/${id}/attendance`);
    return await res.json();
  },

  async updateAttendance(meetingId, participantId, payload) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/attendance/${participantId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  async createAttendance(meetingId, payload) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/attendance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  // Feature 2: Meeting Preparation & Planning
  async generateMeetingPlan(payload) {
    const res = await fetch(`${API_BASE}/api/meetings/meeting-plan/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  async generateMeetingPlanForMeeting(meetingId, payload) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/meeting-plan/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {})
    });
    return await res.json();
  },

  async getMeetingPlan(meetingId) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/meeting-plan`);
    return await res.json();
  },

  async saveMeetingPlan(meetingId, payload) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/meeting-plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  // Feature 3: Role-Based Contributions
  async getRoleContributions(meetingId) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/role-contributions`);
    return await res.json();
  },

  // Feature 4: Topic Coverage
  async getTopicCoverage(meetingId) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/topic-coverage`);
    return await res.json();
  },

  async getExpectedTopics(meetingId) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/expected-topics`);
    return await res.json();
  },

  // Feature 5: Agenda Drift
  async getAgendaDrift(meetingId) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/agenda-drift`);
    return await res.json();
  },

  async submitDriftFeedback(meetingId, driftId, feedback) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/agenda-drift/${driftId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback })
    });
    return await res.json();
  },

  // Feature 6: Silent Participant / Participation Gaps
  async getParticipationGaps(meetingId) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/participation-gaps`);
    return await res.json();
  },

  // Feature 7: Recurring Topics
  async getMeetingRecurringTopics(meetingId) {
    const res = await fetch(`${API_BASE}/api/meetings/${meetingId}/recurring-topics`);
    return await res.json();
  },

  async getGlobalRecurringTopics(status = 'all') {
    const res = await fetch(`${API_BASE}/api/analytics/recurring-topics?status=${encodeURIComponent(status)}`);
    return await res.json();
  }
};
