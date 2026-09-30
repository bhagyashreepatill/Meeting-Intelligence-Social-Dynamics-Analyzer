/**
 * Meeting Intelligence & Social Dynamics Analyzer
 * Main Application Orchestrator & Dynamics Engine
 */

// Global State
const State = {
  currentMeetingId: null,
  meetings: [],
  meeting: null,
  transcript: [],
  participants: [],
  actionItems: [],
  ideas: [],
  ideaJourneys: [],
  attributionShifts: [],
  decisions: [],
  topics: [],
  interactions: [],
  healthTimeline: [],
  temporalShifts: null,
  replayState: null,
  keyframes: [],
  totalDuration: 2700,

  // Advanced Extensions State (Features 1 - 7)
  attendanceSummary: null,
  meetingPlan: null,
  topicCoverage: null,
  roleContributions: null,
  agendaDrift: null,
  participationGaps: null,
  recurringTopics: null,
  attendanceChart: null,
  activeRecurringFilter: 'all',
  generatedPlanDraft: null,

  // Replay Dynamics
  currentTime: 0,
  isPlaying: false,
  replayTimer: null,
  playbackSpeed: 1,

  // Visual Renderers
  mainGraph: null,
  replayGraph: null,
  speakingChart: null,
  turnChart: null,
  compareChart: null,

  // Active Filters
  transcriptSearch: '',
  transcriptSpeaker: 'all',
  transcriptTopic: 'all',
  actionStatusFilter: 'all',
  activeQuartile: 'entire',
  graphEdgeFilter: 'all'
};

// Utilities
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) seconds = 0;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Global modal trigger for Cytoscape node tap
window.showNodeDetailsModal = function(nodeData) {
  const modal = document.getElementById('nodeDetailsModal');
  const title = document.getElementById('nodeModalTitle');
  const body = document.getElementById('nodeModalBody');
  if (!modal || !title || !body) return;

  title.textContent = `Participant: ${nodeData.label}`;
  body.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
      <div style="background: rgba(255,255,255,0.04); padding: 0.85rem; border-radius: 8px;">
        <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">Speaking Time</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #fff;">${formatTime(nodeData.speakingTime || 0)} (${nodeData.speakingPct || 0}%)</div>
      </div>
      <div style="background: rgba(255,255,255,0.04); padding: 0.85rem; border-radius: 8px;">
        <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">Dialogue Turns</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #fff;">${nodeData.turnCount || 0} turns</div>
      </div>
      <div style="background: rgba(255,255,255,0.04); padding: 0.85rem; border-radius: 8px;">
        <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">Interruptions Made</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #fb7185;">${nodeData.interruptionsMade || 0}</div>
      </div>
      <div style="background: rgba(255,255,255,0.04); padding: 0.85rem; border-radius: 8px;">
        <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">Interruptions Received</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #fbbf24;">${nodeData.interruptionsReceived || 0}</div>
      </div>
    </div>
    <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">
      Neutral observation note: Metrics reflect empirical dialogue turn duration and sequence cadence recorded during the session.
    </p>
  `;
  modal.classList.add('open');
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigationTabs();
  setupReplayControls();
  setupModals();
  setupFilters();
  setupIntegrations();
  setupExports();

  await loadMeetingsList();
});

// Setup Navigation Tabs
function setupNavigationTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(`pane-${tabName}`);
      if (targetPane) targetPane.classList.add('active');

      // Refresh graphs when switching to them
      if (tabName === 'graph' && State.mainGraph) {
        setTimeout(() => loadSocialGraph(), 50);
      } else if (tabName === 'replay' && State.replayGraph) {
        setTimeout(() => updateReplayGraphState(), 50);
      }
    });
  });
}

// Load Meetings List & Seed if Empty
async function loadMeetingsList() {
  try {
    let meetings = await API.getMeetings();
    if (!meetings || meetings.length === 0) {
      // Seed Demo Meeting
      const seedRes = await API.seedDemo();
      meetings = await API.getMeetings();
    }

    State.meetings = meetings || [];
    const select = document.getElementById('meetingSelect');
    if (!select) return;

    select.innerHTML = '';
    State.meetings.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = `${m.title} (${m.date || 'Demo'})`;
      select.appendChild(opt);
    });

    select.addEventListener('change', (e) => {
      loadMeetingData(parseInt(e.target.value));
    });

    if (State.meetings.length > 0) {
      select.value = State.meetings[0].id;
      await loadMeetingData(State.meetings[0].id);
    }
  } catch (err) {
    console.error('Failed to load meetings:', err);
    showToast('Failed to initialize meetings list', 'error');
  }
}

// Load All Meeting Intelligence Artifacts in Parallel
async function loadMeetingData(meetingId) {
  State.currentMeetingId = meetingId;
  pauseReplay();
  State.currentTime = 0;

  try {
    const [
      meeting,
      transcript,
      participants,
      actionItems,
      ideasObj,
      ideaJourneys,
      attributionShifts,
      decisions,
      topics,
      replayInit,
      healthTimeline,
      temporalShifts,
      attendanceSummary,
      meetingPlan,
      topicCoverage,
      roleContributions,
      agendaDrift,
      participationGaps,
      recurringTopics
    ] = await Promise.all([
      API.getMeeting(meetingId),
      API.getTranscript(meetingId),
      API.getParticipants(meetingId),
      API.getActionItems(meetingId),
      API.getIdeas(meetingId),
      API.getIdeaJourneys(meetingId),
      API.getAttributionShifts(meetingId),
      API.getDecisions(meetingId),
      API.getTopics(meetingId),
      API.getReplayState(meetingId, 0),
      API.getHealthTimeline(meetingId),
      API.getTemporalShifts(meetingId),
      API.getAttendance(meetingId).catch(err => { console.warn('Attendance load error:', err); return null; }),
      API.getMeetingPlan(meetingId).catch(err => { console.warn('Meeting plan load error:', err); return null; }),
      API.getTopicCoverage(meetingId).catch(err => { console.warn('Topic coverage load error:', err); return null; }),
      API.getRoleContributions(meetingId).catch(err => { console.warn('Role contributions load error:', err); return null; }),
      API.getAgendaDrift(meetingId).catch(err => { console.warn('Agenda drift load error:', err); return null; }),
      API.getParticipationGaps(meetingId).catch(err => { console.warn('Participation gaps load error:', err); return null; }),
      API.getMeetingRecurringTopics(meetingId).catch(err => { console.warn('Recurring topics load error:', err); return null; })
    ]);

    State.meeting = meeting;
    State.transcript = transcript || [];
    State.participants = participants || [];
    State.actionItems = actionItems || [];
    State.ideas = ideasObj.ideas || [];
    State.ideaJourneys = ideaJourneys || [];
    State.attributionShifts = attributionShifts || [];
    State.decisions = decisions || [];
    State.topics = topics || [];
    State.healthTimeline = healthTimeline || [];
    State.temporalShifts = temporalShifts || null;
    State.replayState = replayInit;
    State.keyframes = replayInit.keyframes || [];
    State.totalDuration = meeting.duration || 2700;

    State.attendanceSummary = attendanceSummary;
    State.meetingPlan = meetingPlan;
    State.topicCoverage = topicCoverage;
    State.roleContributions = roleContributions;
    State.agendaDrift = agendaDrift;
    State.participationGaps = participationGaps;
    State.recurringTopics = recurringTopics;

    // Update Badges & Readouts
    updateHeaderCounters();
    renderOverview();
    renderTranscript();
    renderActionItems();
    renderParticipation();
    renderIdeas();
    renderDecisions();
    renderTopics();
    loadSocialGraph();
    initReplayStudio();
    renderIntegrations();

    // Features 1 - 7 Renderers
    renderPreparation();
    renderAttendance();
    renderExpectedVsActual();
    renderAgendaDrift();
    renderRecurringTopics(State.activeRecurringFilter || 'all');

    showToast(`Loaded "${meeting.title}" analytics`, 'info');
  } catch (err) {
    console.error('Error loading meeting data:', err);
    showToast('Error loading meeting analysis', 'error');
  }
}

function updateHeaderCounters() {
  document.getElementById('tabBadgeTranscript').textContent = State.transcript.length;
  document.getElementById('tabBadgeActions').textContent = State.actionItems.length;
  document.getElementById('tabBadgeIdeas').textContent = State.ideas.length;
  document.getElementById('tabBadgeDecisions').textContent = State.decisions.length;
  document.getElementById('tabBadgeTopics').textContent = State.topics.length;
}

// ==================== OVERVIEW RENDERER ====================
function renderOverview() {
  const pCount = State.participants.length;
  const aCount = State.actionItems.length;
  const dCount = State.decisions.length;
  const uCount = State.topics.filter(t => t.status === 'Unresolved').length;

  const setTxt = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setTxt('overviewParticipantsCount', pCount);
  setTxt('overviewAttendanceRate', State.attendanceSummary ? `${State.attendanceSummary.average_attendance_percentage}%` : '100%');
  setTxt('overviewLateArrivals', State.attendanceSummary ? State.attendanceSummary.late_arrivals_count : 0);
  setTxt('overviewActionsCount', aCount);
  setTxt('overviewDecisionsCount', dCount);
  setTxt('overviewTopicCoverage', State.topicCoverage ? `${State.topicCoverage.coverage_percentage}%` : (State.meetingPlan ? '0%' : 'N/A'));
  setTxt('overviewAgendaDrift', State.agendaDrift ? State.agendaDrift.drift_count : 0);
  setTxt('overviewRecurringTopics', State.recurringTopics ? State.recurringTopics.total_recurring_count : 0);
  setTxt('overviewParticipationGaps', State.participationGaps ? State.participationGaps.gap_count : 0);
  setTxt('overviewUnresolvedCount', uCount);

  // Render Speaking Chart
  renderSpeakingChart();

  // Render Health Timeline
  renderHealthTimeline();
}

function renderSpeakingChart() {
  const ctx = document.getElementById('speakingChart');
  if (!ctx) return;

  if (State.speakingChart) {
    State.speakingChart.destroy();
  }

  const labels = State.participants.map(p => p.name);
  const data = State.participants.map(p => p.speaking_percentage);
  const colors = State.participants.map(p => p.avatar_color || '#6366f1');

  State.speakingChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Speaking Share (%)',
        data: data,
        backgroundColor: colors,
        borderRadius: 8,
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.raw}% (${formatTime(State.participants[ctx.dataIndex]?.speaking_time || 0)})`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#f8fafc', font: { weight: '600' } }
        }
      }
    }
  });
}

function renderHealthTimeline() {
  const container = document.getElementById('healthTimelineContainer');
  if (!container) return;
  container.innerHTML = '';

  if (!State.healthTimeline || State.healthTimeline.length === 0) {
    container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No interval observations available.</div>';
    return;
  }

  State.healthTimeline.forEach(obs => {
    const card = document.createElement('div');
    card.style.cssText = 'background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.75rem 1rem; display: flex; justify-content: space-between; align-items: center;';

    card.innerHTML = `
      <div>
        <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-cyan); font-weight: 700; background: rgba(6,182,212,0.1); padding: 0.2rem 0.5rem; border-radius: 4px; margin-right: 0.5rem;">${obs.interval}</span>
        <span style="font-weight: 600; color: #f1f5f9; font-size: 0.85rem;">${obs.cadence}</span>
      </div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">${obs.observation}</div>
    `;
    container.appendChild(card);
  });
}

// ==================== TRANSCRIPT RENDERER ====================
function renderTranscript() {
  const list = document.getElementById('transcriptList');
  const speakerSelect = document.getElementById('transcriptSpeakerFilter');
  const topicSelect = document.getElementById('transcriptTopicFilter');
  if (!list) return;

  // Populate speaker filter
  if (speakerSelect) {
    speakerSelect.innerHTML = '<option value="all">All Speakers</option>';
    State.participants.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.name;
      opt.textContent = p.name;
      speakerSelect.appendChild(opt);
    });
    speakerSelect.value = State.transcriptSpeaker;
  }

  // Populate topic filter
  if (topicSelect) {
    topicSelect.innerHTML = '<option value="all">All Topics</option>';
    State.topics.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.name;
      opt.textContent = t.name;
      topicSelect.appendChild(opt);
    });
    topicSelect.value = State.transcriptTopic;
  }

  // Filter segments
  const query = State.transcriptSearch.toLowerCase();
  const filtered = State.transcript.filter(seg => {
    const matchesSpeaker = State.transcriptSpeaker === 'all' || seg.speaker_name === State.transcriptSpeaker;
    const matchesQuery = !query || seg.text.toLowerCase().includes(query) || seg.speaker_name.toLowerCase().includes(query);
    
    let matchesTopic = true;
    if (State.transcriptTopic !== 'all') {
      const matchedTopic = State.topics.find(t => t.name === State.transcriptTopic);
      matchesTopic = matchedTopic && (seg.start_time >= matchedTopic.start_time && seg.start_time <= matchedTopic.end_time);
    }
    return matchesSpeaker && matchesQuery && matchesTopic;
  });

  list.innerHTML = '';
  if (filtered.length === 0) {
    list.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-muted);">No transcript dialogue matches current filters.</div>';
    return;
  }

  filtered.forEach(seg => {
    const card = document.createElement('div');
    card.className = 'transcript-turn-card';
    card.setAttribute('data-turn', seg.turn_number);
    card.setAttribute('data-time', seg.start_time);

    let highlightedText = seg.text;
    if (query) {
      const reg = new RegExp(`(${query})`, 'gi');
      highlightedText = highlightedText.replace(reg, '<mark>$1</mark>');
    }

    // Find participant color
    const p = State.participants.find(part => part.name === seg.speaker_name);
    const color = p ? p.avatar_color : '#6366f1';

    card.innerHTML = `
      <div class="turn-meta">
        <span class="turn-speaker-badge" style="color: ${color};">
          <span style="width: 8px; height: 8px; border-radius: 50%; background: ${color};"></span>
          ${seg.speaker_name}
        </span>
        <span class="turn-timestamp">[${formatTime(seg.start_time)}]</span>
      </div>
      <div class="turn-text">${highlightedText}</div>
    `;

    card.addEventListener('click', () => {
      seekToTime(seg.start_time);
      showToast(`Jumped to [${formatTime(seg.start_time)}] - ${seg.speaker_name}`, 'info');
    });

    list.appendChild(card);
  });
}

function setupFilters() {
  const searchInput = document.getElementById('transcriptSearch');
  const speakerSelect = document.getElementById('transcriptSpeakerFilter');
  const topicSelect = document.getElementById('transcriptTopicFilter');
  const resetBtn = document.getElementById('btnResetTranscriptFilter');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      State.transcriptSearch = e.target.value;
      renderTranscript();
    });
  }

  if (speakerSelect) {
    speakerSelect.addEventListener('change', (e) => {
      State.transcriptSpeaker = e.target.value;
      renderTranscript();
    });
  }

  if (topicSelect) {
    topicSelect.addEventListener('change', (e) => {
      State.transcriptTopic = e.target.value;
      renderTranscript();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      State.transcriptSearch = '';
      State.transcriptSpeaker = 'all';
      State.transcriptTopic = 'all';
      if (searchInput) searchInput.value = '';
      if (speakerSelect) speakerSelect.value = 'all';
      if (topicSelect) topicSelect.value = 'all';
      renderTranscript();
    });
  }

  const actionFilter = document.getElementById('actionFilterStatus');
  if (actionFilter) {
    actionFilter.addEventListener('change', (e) => {
      State.actionStatusFilter = e.target.value;
      renderActionItems();
    });
  }

  const graphFilter = document.getElementById('graphEdgeFilter');
  if (graphFilter) {
    graphFilter.addEventListener('change', (e) => {
      State.graphEdgeFilter = e.target.value;
      loadSocialGraph(e.target.value);
    });
  }
}

// ==================== ACTION ITEMS RENDERER ====================
function renderActionItems() {
  const tbody = document.getElementById('actionsTableBody');
  const lifecycleStats = document.getElementById('actionLifecycleStats');
  if (!tbody) return;

  const total = State.actionItems.length;
  const confirmed = State.actionItems.filter(a => a.status === 'Confirmed').length;
  const assigned = State.actionItems.filter(a => a.status === 'Assigned').length;
  const inProgress = State.actionItems.filter(a => a.status === 'In Progress').length;
  const completed = State.actionItems.filter(a => a.status === 'Completed').length;
  const detected = State.actionItems.filter(a => a.status === 'Detected').length;

  if (lifecycleStats) {
    lifecycleStats.innerHTML = `
      <div style="font-weight: 700; color: #fff;">Lifecycle Funnel:</div>
      <div><span style="color: #818cf8; font-weight: 700;">${total}</span> Total</div>
      <div style="color: var(--text-muted);">→</div>
      <div><span style="color: #22d3ee; font-weight: 700;">${detected}</span> Detected</div>
      <div style="color: var(--text-muted);">→</div>
      <div><span style="color: #34d399; font-weight: 700;">${confirmed + assigned}</span> Confirmed</div>
      <div style="color: var(--text-muted);">→</div>
      <div><span style="color: #fbbf24; font-weight: 700;">${inProgress}</span> In Progress</div>
      <div style="color: var(--text-muted);">→</div>
      <div><span style="color: #10b981; font-weight: 700;">${completed}</span> Completed</div>
    `;
  }

  const readyBadge = document.getElementById('integrationActionCount');
  if (readyBadge) {
    const readyCount = State.actionItems.filter(a => ['Confirmed', 'Assigned', 'In Progress'].includes(a.status)).length;
    readyBadge.textContent = `${readyCount} Confirmed Tasks Ready`;
  }

  const filtered = State.actionItems.filter(a => {
    if (State.actionStatusFilter === 'all') return true;
    return a.status === State.actionStatusFilter;
  });

  tbody.innerHTML = '';
  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No action items match the selected status filter.</td></tr>';
    return;
  }

  filtered.forEach(item => {
    const tr = document.createElement('tr');
    tr.className = 'action-row';

    const pClass = item.priority === 'High' ? 'badge-high' : item.priority === 'Medium' ? 'badge-medium' : 'badge-low';
    const sClass = item.status === 'Confirmed' || item.status === 'Completed' ? 'badge-confirmed' : item.status === 'Rejected' ? 'badge-rejected' : 'badge-detected';

    tr.innerHTML = `
      <td class="task-cell">
        <div>${item.task}</div>
        ${item.evidence ? `<span class="task-evidence">Quote: "${item.evidence}"</span>` : ''}
      </td>
      <td>
        <span style="font-weight: 600; color: #f8fafc;">${item.owner || 'Unknown'}</span>
      </td>
      <td>
        <span style="font-family: var(--font-mono); font-size: 0.8rem; color: #94a3b8;">${item.due_date || 'Unknown'}</span>
      </td>
      <td>
        <span class="badge ${pClass}">${item.priority}</span>
      </td>
      <td>
        <span style="font-family: var(--font-mono); font-size: 0.8rem; color: #c7d2fe;">${Math.round(item.confidence * 100)}%</span>
      </td>
      <td>
        <span class="badge ${sClass}">${item.status}</span>
      </td>
      <td style="text-align: right;">
        <div class="action-btn-group" style="justify-content: flex-end;">
          ${item.status !== 'Confirmed' ? `
            <button class="btn btn-secondary btn-sm" onclick="handleAcceptAction(${item.id})" title="Confirm this action item">
              Accept
            </button>
          ` : ''}
          <button class="btn btn-secondary btn-sm" onclick="handleOpenEditActionModal(${item.id})" title="Edit task details">
            Edit
          </button>
          ${item.status !== 'Rejected' ? `
            <button class="btn btn-secondary btn-sm" style="color: #fb7185;" onclick="handleRejectAction(${item.id})" title="Reject false extraction">
              Reject
            </button>
          ` : ''}
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.handleAcceptAction = async function(id) {
  try {
    const res = await API.acceptActionItem(id);
    const item = State.actionItems.find(a => a.id === id);
    if (item) item.status = res.status;
    renderActionItems();
    showToast('Action item confirmed!', 'success');
  } catch (err) {
    showToast('Failed to accept action item', 'error');
  }
};

window.handleRejectAction = async function(id) {
  try {
    const res = await API.rejectActionItem(id);
    const item = State.actionItems.find(a => a.id === id);
    if (item) item.status = res.status;
    renderActionItems();
    showToast('Action item rejected', 'info');
  } catch (err) {
    showToast('Failed to reject action item', 'error');
  }
};

window.handleOpenEditActionModal = function(id) {
  const item = State.actionItems.find(a => a.id === id);
  if (!item) return;

  document.getElementById('editItemId').value = item.id;
  document.getElementById('editTask').value = item.task;
  document.getElementById('editOwner').value = item.owner || '';
  document.getElementById('editDueDate').value = item.due_date || '';
  document.getElementById('editPriority').value = item.priority || 'Medium';
  document.getElementById('editStatus').value = item.status || 'Detected';

  const modal = document.getElementById('editActionModal');
  if (modal) modal.classList.add('open');
};

// ==================== PARTICIPATION RENDERER ====================
function renderParticipation() {
  renderTurnCadence();
  renderParticipantCards();
  renderTemporalShifts();
  renderParticipationGaps();
}

function renderTurnCadence() {
  const ctx = document.getElementById('turnChart');
  const statsContainer = document.getElementById('turnCadenceStats');
  if (!ctx || !statsContainer) return;

  if (State.turnChart) {
    State.turnChart.destroy();
  }

  const labels = State.participants.map(p => p.name);
  const avgTurns = State.participants.map(p => p.avg_turn_length || 0);

  State.turnChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Avg Turn Length (seconds)',
        data: avgTurns,
        backgroundColor: '#6366f1',
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#f8fafc', font: { weight: '600' } }
        }
      }
    }
  });

  // Calculate meeting aggregates
  const allTurns = State.participants.map(p => p.avg_turn_length || 0);
  const avgCadence = allTurns.length ? Math.round(allTurns.reduce((a, b) => a + b, 0) / allTurns.length) : 0;
  const totalTurns = State.participants.reduce((acc, p) => acc + (p.turn_count || 0), 0);

  statsContainer.innerHTML = `
    <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
      <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">Average Turn Cadence</div>
      <div style="font-size: 1.5rem; font-weight: 700; color: #fff;">${avgCadence} seconds</div>
      <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem;">Mean length of dialogue turns across all speakers</div>
    </div>
    <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
      <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">Total Conversational Turns</div>
      <div style="font-size: 1.5rem; font-weight: 700; color: #22d3ee;">${totalTurns} turns</div>
      <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem;">Cadence transitions throughout the 45-minute sprint</div>
    </div>
  `;

  // Setup Quartile buttons
  const qButtons = document.querySelectorAll('#quartileButtons button');
  qButtons.forEach(btn => {
    btn.onclick = () => {
      qButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const qKey = btn.getAttribute('data-quartile');
      filterTurnCadenceByQuartile(qKey);
    };
  });
}

function filterTurnCadenceByQuartile(quartileKey) {
  if (!State.temporalShifts || !State.temporalShifts.quartiles) return;
  const qData = State.temporalShifts.quartiles[quartileKey] || State.temporalShifts.quartiles['entire'];
  if (!qData) return;

  const labels = Object.keys(qData);
  const data = Object.values(qData);

  if (State.turnChart) {
    State.turnChart.data.labels = labels;
    State.turnChart.data.datasets[0].data = data;
    State.turnChart.update();
  }
}

function renderParticipantCards() {
  const grid = document.getElementById('participantCardsGrid');
  if (!grid) return;
  grid.innerHTML = '';

  State.participants.forEach(p => {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.style.flexDirection = 'column';
    card.style.alignItems = 'stretch';
    card.style.gap = '0.75rem';

    card.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.6rem;">
        <div style="display: flex; align-items: center; gap: 0.6rem;">
          <span style="width: 14px; height: 14px; border-radius: 50%; background: ${p.avatar_color || '#6366f1'};"></span>
          <span style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700;">${p.name}</span>
        </div>
        <span class="badge" style="background: rgba(99,102,241,0.15); color: #818cf8;">${p.speaking_percentage}% Share</span>
      </div>

      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; font-size: 0.8rem;">
        <div><span style="color: var(--text-muted);">Speaking:</span> <strong style="color: #fff;">${formatTime(p.speaking_time)}</strong></div>
        <div><span style="color: var(--text-muted);">Turns:</span> <strong style="color: #fff;">${p.turn_count}</strong></div>
        <div><span style="color: var(--text-muted);">Avg Turn:</span> <strong style="color: #fff;">${p.avg_turn_length}s</strong></div>
        <div><span style="color: var(--text-muted);">Median:</span> <strong style="color: #fff;">${p.median_turn_length}s</strong></div>
        <div><span style="color: var(--text-muted);">Longest:</span> <strong style="color: #fff;">${p.longest_turn}s</strong></div>
        <div><span style="color: var(--text-muted);">Shortest:</span> <strong style="color: #fff;">${p.shortest_turn}s</strong></div>
        <div><span style="color: var(--text-muted);">Interrupts Made:</span> <strong style="color: #fb7185;">${p.interruptions_made}</strong></div>
        <div><span style="color: var(--text-muted);">Received:</span> <strong style="color: #fbbf24;">${p.interruptions_received}</strong></div>
      </div>
    `;
    grid.appendChild(card);
  });
}

function renderTemporalShifts() {
  const container = document.getElementById('temporalShiftsContainer');
  if (!container) return;
  container.innerHTML = '';

  if (!State.temporalShifts || !State.temporalShifts.temporal_shifts) {
    container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">Temporal shift analysis not available.</div>';
    return;
  }

  const shifts = State.temporalShifts.temporal_shifts;
  Object.keys(shifts).forEach(sp => {
    const data = shifts[sp];
    const card = document.createElement('div');
    card.style.cssText = 'background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;';

    card.innerHTML = `
      <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.5rem; color: #fff;">${sp}</div>
      <div style="display: flex; gap: 0.75rem; align-items: center; font-size: 0.85rem;">
        <div>Beginning: <strong style="color: #818cf8;">${data.beginning}%</strong></div>
        <div style="color: var(--text-muted);">→</div>
        <div>Middle: <strong style="color: #22d3ee;">${data.middle}%</strong></div>
        <div style="color: var(--text-muted);">→</div>
        <div>End: <strong style="color: #34d399;">${data.end}%</strong></div>
      </div>
      <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.4rem;">
        Pattern: ${data.pattern}
      </div>
    `;
    container.appendChild(card);
  });
}

// ==================== IDEAS & PROVENANCE RENDERER ====================
function renderIdeas() {
  renderAttributionShifts();
  renderIdeaJourneys();
  renderIdeasTable();
}

function renderAttributionShifts() {
  const container = document.getElementById('attributionShiftsContainer');
  if (!container) return;
  container.innerHTML = '';

  if (!State.attributionShifts || State.attributionShifts.length === 0) {
    return;
  }

  State.attributionShifts.forEach(shift => {
    const box = document.createElement('div');
    box.className = 'attribution-shift-box';
    box.innerHTML = `
      <div class="attribution-shift-icon">⚠</div>
      <div class="attribution-shift-content">
        <h4>Potential Idea Attribution Shift Detected</h4>
        <p>
          <strong>Original Concept:</strong> "${shift.original_quote}" introduced by <strong>${shift.original_speaker}</strong> at [${formatTime(shift.original_timestamp)}].<br>
          <strong>Later Similar Statement:</strong> "${shift.later_quote}" spoken by <strong>${shift.later_speaker}</strong> at [${formatTime(shift.later_timestamp)}].<br>
          <strong>Semantic Similarity:</strong> <span style="color: var(--accent-amber); font-weight: 700;">${shift.semantic_similarity_pct}%</span> | 
          <strong>Explicit Attribution:</strong> <span style="color: #cbd5e1;">${shift.explicit_attribution ? 'Detected' : 'Not detected in dialogue'}</span>
        </p>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem;">
          Objective detection signal: Semantic phrasing similarity indicates concept convergence; no psychological intention or attribution judgment is implied.
        </div>
      </div>
    `;
    container.appendChild(box);
  });
}

function renderIdeaJourneys() {
  const container = document.getElementById('ideaJourneysContainer');
  if (!container) return;
  container.innerHTML = '';

  if (!State.ideaJourneys || State.ideaJourneys.length === 0) {
    container.innerHTML = '<div style="color: var(--text-muted); padding: 1.5rem;">No multi-stage idea provenance chains detected.</div>';
    return;
  }

  State.ideaJourneys.forEach(journey => {
    const wrapper = document.createElement('div');
    wrapper.style.marginBottom = '2rem';

    let stepsHtml = '';
    (journey.steps || []).forEach(step => {
      const stageClass = `stage-${step.stage.toLowerCase()}`;
      stepsHtml += `
        <div class="journey-step-card">
          <div class="journey-step-marker"></div>
          <div class="journey-step-header">
            <span class="journey-step-stage ${stageClass}">${step.stage}</span>
            <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted);">[${formatTime(step.timestamp)}]</span>
          </div>
          <div style="font-size: 0.9rem; font-weight: 600; color: #fff;">
            ${step.speaker ? `<strong>${step.speaker}:</strong> ` : ''}${step.description}
          </div>
          ${step.quote ? `<div class="journey-step-quote">"${step.quote}"</div>` : ''}
        </div>
      `;
    });

    wrapper.innerHTML = `
      <div style="background: rgba(99,102,241,0.06); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 1.25rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
          <h4 style="font-family: var(--font-heading); font-size: 1.1rem; color: #c084fc;">Idea: "${journey.idea_title}"</h4>
          <span class="badge badge-confirmed">Origin: ${journey.originator}</span>
        </div>
        <div class="journey-timeline">
          ${stepsHtml}
        </div>
      </div>
    `;
    container.appendChild(wrapper);
  });
}

function renderIdeasTable() {
  const tbody = document.getElementById('ideasTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  State.ideas.forEach(idea => {
    const tr = document.createElement('tr');
    tr.className = 'action-row';
    tr.innerHTML = `
      <td class="task-cell">${idea.text}</td>
      <td><strong>${idea.speaker}</strong></td>
      <td><span style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">${idea.time_display || formatTime(idea.timestamp)}</span></td>
      <td><span style="font-family: var(--font-mono); font-size: 0.8rem; color: #c7d2fe;">${Math.round(idea.confidence * 100)}%</span></td>
      <td><span class="badge badge-detected">${idea.lifecycle_stage || 'Introduced'}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

// ==================== DECISIONS RENDERER ====================
function renderDecisions() {
  const tbody = document.getElementById('decisionsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (State.decisions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No consensus decisions recorded.</td></tr>';
    return;
  }

  State.decisions.forEach(d => {
    const tr = document.createElement('tr');
    tr.className = 'action-row';
    tr.innerHTML = `
      <td class="task-cell">
        <strong style="color: #34d399;">${d.text}</strong>
      </td>
      <td><span style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">[${formatTime(d.timestamp)}]</span></td>
      <td><span style="font-weight: 600;">${d.participants_involved || 'Team'}</span></td>
      <td><span style="color: var(--text-secondary); font-size: 0.85rem;">${d.related_idea_id ? 'Deployment / Architecture' : 'General consensus'}</span></td>
      <td><span style="font-family: var(--font-mono); font-size: 0.8rem; color: #c7d2fe;">${Math.round(d.confidence * 100)}%</span></td>
      <td style="text-align: right;">
        <button class="btn btn-secondary btn-sm" onclick="seekToTime(${d.timestamp})">Jump to turn</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ==================== TOPICS RENDERER ====================
function renderTopics() {
  const container = document.getElementById('topicsTimelineContainer');
  if (!container) return;
  container.innerHTML = '';

  State.topics.forEach(top => {
    const card = document.createElement('div');
    card.style.cssText = 'background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.1rem 1.25rem; display: flex; align-items: center; justify-content: space-between;';

    const statusBadge = top.status === 'Resolved' 
      ? '<span class="badge badge-confirmed">Resolved</span>' 
      : top.status === 'Partially Resolved'
      ? '<span class="badge badge-medium">Partially Resolved</span>'
      : '<span class="badge badge-high">Unresolved</span>';

    card.innerHTML = `
      <div>
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.3rem;">
          <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-cyan);">[${formatTime(top.start_time)} - ${formatTime(top.end_time)}]</span>
          <h4 style="font-size: 1rem; font-weight: 700; color: #fff;">${top.name}</h4>
          ${statusBadge}
        </div>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0;">${top.evidence || 'Discussion documented in transcript dialogue.'}</p>
      </div>
      <div>
        <button class="btn btn-secondary btn-sm" onclick="seekToTime(${top.start_time})">View Segment</button>
      </div>
    `;
    container.appendChild(card);
  });
}

// ==================== SOCIAL GRAPH RENDERER ====================
async function loadSocialGraph(filterType = 'all') {
  if (!State.currentMeetingId) return;
  try {
    const graphData = await API.getSocialGraph(State.currentMeetingId, filterType);
    if (!State.mainGraph) {
      State.mainGraph = new SocialGraphRenderer('cy-container');
    }
    State.mainGraph.render(graphData);
  } catch (err) {
    console.error('Failed to load social graph:', err);
  }
}

// ==================== REPLAY STUDIO & ENGINE ====================
function initReplayStudio() {
  const slider = document.getElementById('timelineSlider');
  const keyframesBar = document.getElementById('sliderKeyframesBar');
  const totalTimeLabel = document.getElementById('totalTime');

  if (slider) {
    slider.max = State.totalDuration;
    slider.value = 0;
  }
  if (totalTimeLabel) {
    totalTimeLabel.textContent = formatTime(State.totalDuration);
  }

  // Draw Keyframe Markers
  if (keyframesBar) {
    keyframesBar.innerHTML = '';
    State.keyframes.forEach(kf => {
      const marker = document.createElement('div');
      const leftPct = (kf.timestamp / State.totalDuration) * 100;
      marker.className = `keyframe-marker ${kf.type}`;
      marker.style.left = `${leftPct}%`;
      marker.title = `[${formatTime(kf.timestamp)}] ${kf.type.toUpperCase()}: ${kf.label}`;
      keyframesBar.appendChild(marker);
    });
  }

  // Init Replay Graph Renderer
  if (!State.replayGraph && document.getElementById('cy-container-replay')) {
    State.replayGraph = new SocialGraphRenderer('cy-container-replay');
  }
  updateReplayGraphState();
  updateReplaySnapshot(0);
}

function setupReplayControls() {
  const btnPlay = document.getElementById('btnPlayPause');
  const btnPrev = document.getElementById('btnPrevEvent');
  const btnNext = document.getElementById('btnNextEvent');
  const speedBadge = document.getElementById('speedBadge');
  const slider = document.getElementById('timelineSlider');

  if (btnPlay) {
    btnPlay.addEventListener('click', togglePlayPause);
  }

  if (speedBadge) {
    speedBadge.addEventListener('click', () => {
      if (State.playbackSpeed === 1) State.playbackSpeed = 2;
      else if (State.playbackSpeed === 2) State.playbackSpeed = 5;
      else State.playbackSpeed = 1;
      speedBadge.textContent = `${State.playbackSpeed}x`;
    });
  }

  if (slider) {
    slider.addEventListener('input', (e) => {
      seekToTime(parseFloat(e.target.value));
    });
  }

  if (btnPrev) {
    btnPrev.addEventListener('click', () => {
      const prev = [...State.keyframes].reverse().find(kf => kf.timestamp < State.currentTime - 1);
      if (prev) seekToTime(prev.timestamp);
      else seekToTime(0);
    });
  }

  if (btnNext) {
    btnNext.addEventListener('click', () => {
      const next = State.keyframes.find(kf => kf.timestamp > State.currentTime + 1);
      if (next) seekToTime(next.timestamp);
    });
  }
}

function togglePlayPause() {
  if (State.isPlaying) {
    pauseReplay();
  } else {
    startReplay();
  }
}

function startReplay() {
  State.isPlaying = true;
  document.getElementById('playIcon').style.display = 'none';
  document.getElementById('pauseIcon').style.display = 'block';

  if (State.currentTime >= State.totalDuration) {
    State.currentTime = 0;
  }

  State.replayTimer = setInterval(() => {
    State.currentTime += State.playbackSpeed * 1;
    if (State.currentTime >= State.totalDuration) {
      State.currentTime = State.totalDuration;
      pauseReplay();
    }
    updateReplayTick();
  }, 1000);
}

function pauseReplay() {
  State.isPlaying = false;
  clearInterval(State.replayTimer);
  State.replayTimer = null;
  const playIcon = document.getElementById('playIcon');
  const pauseIcon = document.getElementById('pauseIcon');
  if (playIcon) playIcon.style.display = 'block';
  if (pauseIcon) pauseIcon.style.display = 'none';
}

function seekToTime(seconds) {
  State.currentTime = Math.max(0, Math.min(State.totalDuration, seconds));
  updateReplayTick();
}

async function updateReplayTick() {
  // Update slider position & readout
  const slider = document.getElementById('timelineSlider');
  const currTime = document.getElementById('currTime');
  if (slider) slider.value = State.currentTime;
  if (currTime) currTime.textContent = formatTime(State.currentTime);

  // Synchronize snapshot data
  updateReplaySnapshot(State.currentTime);
}

async function updateReplaySnapshot(timestamp) {
  if (!State.currentMeetingId) return;

  try {
    const snapshot = await API.getReplayState(State.currentMeetingId, timestamp);
    
    // Update active speaker tag
    const speakerPill = document.getElementById('activeSpeakerPill');
    const speakerName = document.getElementById('activeSpeakerName');
    const activeTopic = document.getElementById('activeTopicName');

    if (snapshot.current_turn) {
      if (speakerName) speakerName.textContent = `${snapshot.current_turn.speaker} speaking`;
      document.getElementById('replayLiveSpeaker').textContent = snapshot.current_turn.speaker;
      document.getElementById('replayLiveTimestamp').textContent = `[${formatTime(snapshot.current_turn.start_time)}]`;
      document.getElementById('replayLiveQuote').textContent = `"${snapshot.current_turn.text}"`;
    } else {
      if (speakerName) speakerName.textContent = 'Listening / Transition';
    }

    if (activeTopic) {
      activeTopic.textContent = snapshot.active_topic || 'Discussion';
    }

    // Update capsule metrics
    document.getElementById('statActiveParticipants').textContent = snapshot.active_participants ? snapshot.active_participants.length : 0;
    document.getElementById('statActiveIdeas').textContent = snapshot.cumulative_ideas ? snapshot.cumulative_ideas.length : 0;
    document.getElementById('statActiveInterruptions').textContent = snapshot.cumulative_interruptions ? snapshot.cumulative_interruptions.length : 0;
    document.getElementById('statActiveDecisions').textContent = snapshot.cumulative_decisions ? snapshot.cumulative_decisions.length : 0;
    document.getElementById('statActiveActions').textContent = snapshot.cumulative_actions ? snapshot.cumulative_actions.length : 0;

    // Highlight active speaker in Cytoscape graphs
    const currentSp = snapshot.current_turn ? snapshot.current_turn.speaker : null;
    if (State.mainGraph) State.mainGraph.highlightSpeaker(currentSp);
    if (State.replayGraph) State.replayGraph.highlightSpeaker(currentSp);

    // Update Replay Events Feed
    renderReplayEventsFeed(snapshot);
  } catch (err) {
    console.error('Error fetching replay snapshot:', err);
  }
}

async function updateReplayGraphState() {
  if (!State.currentMeetingId || !State.replayGraph) return;
  try {
    const graphData = await API.getSocialGraph(State.currentMeetingId, 'all');
    State.replayGraph.render(graphData);
  } catch (err) {
    console.error('Failed to init replay graph:', err);
  }
}

function renderReplayEventsFeed(snapshot) {
  const feed = document.getElementById('replayEventsFeed');
  if (!feed) return;
  feed.innerHTML = '';

  const events = [];
  (snapshot.cumulative_ideas || []).forEach(i => events.push({ type: 'idea', text: `Idea: "${i.text}" (${i.speaker})`, time: i.timestamp }));
  (snapshot.cumulative_decisions || []).forEach(d => events.push({ type: 'decision', text: `Decision: ${d.text}`, time: d.timestamp }));
  (snapshot.cumulative_actions || []).forEach(a => events.push({ type: 'action', text: `Action: ${a.task} → ${a.owner}`, time: a.timestamp || 0 }));
  (snapshot.cumulative_interruptions || []).forEach(intr => events.push({ type: 'interruption', text: `Interruption: ${intr.speaker_a} → ${intr.speaker_b}`, time: intr.timestamp || 0 }));

  events.sort((a, b) => b.time - a.time);

  if (events.length === 0) {
    feed.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">No events emerged yet. Slide timeline forward.</div>';
    return;
  }

  events.slice(0, 5).forEach(e => {
    const item = document.createElement('div');
    item.style.cssText = 'font-size: 0.8rem; background: rgba(255,255,255,0.02); padding: 0.4rem 0.6rem; border-radius: 4px; display: flex; justify-content: space-between;';
    item.innerHTML = `
      <span style="color: #e2e8f0;">${e.text}</span>
      <span style="font-family: var(--font-mono); color: var(--text-muted); margin-left: 0.5rem;">[${formatTime(e.time)}]</span>
    `;
    feed.appendChild(item);
  });
}

// ==================== INTEGRATIONS DISPATCHER ====================
function setupIntegrations() {
  const btnSlack = document.getElementById('slackDispatchBtn');
  const btnJira = document.getElementById('jiraDispatchBtn');
  const btnTrello = document.getElementById('trelloDispatchBtn');

  if (btnSlack) {
    btnSlack.addEventListener('click', () => dispatchIntegration('slack'));
  }
  if (btnJira) {
    btnJira.addEventListener('click', () => dispatchIntegration('jira'));
  }
  if (btnTrello) {
    btnTrello.addEventListener('click', () => dispatchIntegration('trello'));
  }
}

function renderIntegrations() {
  const readyCount = State.actionItems.filter(a => ['Confirmed', 'Assigned', 'In Progress'].includes(a.status)).length;
  const readyBadge = document.getElementById('integrationActionCount');
  if (readyBadge) {
    readyBadge.textContent = `${readyCount} Confirmed Tasks Ready`;
  }
}

async function dispatchIntegration(platform) {
  if (!State.currentMeetingId) return;
  const log = document.getElementById('integrationLog');
  showToast(`Dispatching to ${platform.toUpperCase()}...`, 'info');

  try {
    const res = await API.dispatchIntegration(platform, {
      meeting_id: State.currentMeetingId
    });

    if (log) {
      log.textContent = `[${new Date().toLocaleTimeString()}] ${platform.toUpperCase()} SUCCESS:\n` + JSON.stringify(res, null, 2);
    }
    showToast(`Successfully dispatched to ${platform.toUpperCase()}`, 'success');
  } catch (err) {
    if (log) {
      log.textContent = `[${new Date().toLocaleTimeString()}] ${platform.toUpperCase()} ERROR:\n` + err.message;
    }
    showToast(`Failed to dispatch to ${platform.toUpperCase()}`, 'error');
  }
}

// ==================== MULTI-MEETING COMPARISON ====================
async function runComparison() {
  const container = document.getElementById('compareMetricsContainer');
  const ctx = document.getElementById('compareChart');
  if (!container) return;

  const ids = State.meetings.map(m => m.id).join(',');
  try {
    const comparisons = await API.compareMeetings(ids);
    renderComparisonTable(comparisons, container);

    if (ctx && comparisons.length > 0) {
      if (State.compareChart) State.compareChart.destroy();

      State.compareChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: comparisons.map(c => c.title),
          datasets: [
            { label: 'Conversational Turns', data: comparisons.map(c => c.total_turns), backgroundColor: '#6366f1' },
            { label: 'Action Items', data: comparisons.map(c => c.action_items_count), backgroundColor: '#fbbf24' },
            { label: 'Decisions', data: comparisons.map(c => c.decisions_count), backgroundColor: '#34d399' },
            { label: 'Interruptions', data: comparisons.map(c => c.total_interruptions), backgroundColor: '#fb7185' }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
            x: { ticks: { color: '#f8fafc', font: { weight: '600' } } }
          }
        }
      });
    }
  } catch (err) {
    console.error('Failed to run comparison:', err);
  }
}

function renderComparisonTable(comparisons, container) {
  let html = `
    <table class="action-items-table">
      <thead>
        <tr>
          <th>Meeting Title</th>
          <th>Date</th>
          <th>Participants</th>
          <th>Total Turns</th>
          <th>Avg Turn (s)</th>
          <th>Interruptions</th>
          <th>Action Items</th>
          <th>Decisions</th>
          <th>Unresolved</th>
        </tr>
      </thead>
      <tbody>
  `;

  comparisons.forEach(c => {
    html += `
      <tr class="action-row">
        <td><strong>${c.title}</strong></td>
        <td>${c.date}</td>
        <td>${c.participant_count}</td>
        <td>${c.total_turns}</td>
        <td>${c.average_turn_length}s</td>
        <td><span style="color: #fb7185; font-weight: 700;">${c.total_interruptions}</span></td>
        <td><span style="color: #fbbf24; font-weight: 700;">${c.action_items_count}</span></td>
        <td><span style="color: #34d399; font-weight: 700;">${c.decisions_count}</span></td>
        <td><span style="color: #22d3ee; font-weight: 700;">${c.unresolved_topics_count}</span></td>
      </tr>
    `;
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

// ==================== MODALS & FORMS ====================
function setupModals() {
  const uploadModal = document.getElementById('uploadModal');
  const btnUpload = document.getElementById('btnUploadModal');
  const btnCloseUpload = document.getElementById('btnCloseUploadModal');
  const btnCancelUpload = document.getElementById('btnCancelUpload');
  const uploadForm = document.getElementById('uploadForm');

  if (btnUpload && uploadModal) {
    btnUpload.addEventListener('click', () => uploadModal.classList.add('open'));
  }
  if (btnCloseUpload && uploadModal) {
    btnCloseUpload.addEventListener('click', () => uploadModal.classList.remove('open'));
  }
  if (btnCancelUpload && uploadModal) {
    btnCancelUpload.addEventListener('click', () => uploadModal.classList.remove('open'));
  }

  if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('uploadTitle').value;
      const fileInput = document.getElementById('uploadFile');
      const rawText = document.getElementById('uploadRawText').value;

      const formData = new FormData();
      formData.append('title', title);
      if (fileInput.files.length > 0) {
        formData.append('file', fileInput.files[0]);
      } else if (rawText.trim()) {
        formData.append('raw_text', rawText.trim());
      } else {
        showToast('Please select a file or paste dialogue text.', 'error');
        return;
      }

      showToast('Processing & analyzing meeting transcript...', 'info');
      uploadModal.classList.remove('open');

      try {
        const res = await API.uploadMeeting(formData);
        showToast('Meeting processed successfully!', 'success');
        await loadMeetingsList();
        if (res.meeting_id) {
          document.getElementById('meetingSelect').value = res.meeting_id;
          await loadMeetingData(res.meeting_id);
        }
      } catch (err) {
        showToast('Failed to process transcript: ' + err.message, 'error');
      }
    });
  }

  // Edit Action Modal Form
  const editModal = document.getElementById('editActionModal');
  const btnCloseEdit = document.getElementById('btnCloseEditModal');
  const btnCancelEdit = document.getElementById('btnCancelEdit');
  const editForm = document.getElementById('editActionForm');

  if (btnCloseEdit && editModal) btnCloseEdit.addEventListener('click', () => editModal.classList.remove('open'));
  if (btnCancelEdit && editModal) btnCancelEdit.addEventListener('click', () => editModal.classList.remove('open'));

  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const id = parseInt(document.getElementById('editItemId').value);
      const payload = {
        task: document.getElementById('editTask').value,
        owner: document.getElementById('editOwner').value,
        due_date: document.getElementById('editDueDate').value,
        priority: document.getElementById('editPriority').value,
        status: document.getElementById('editStatus').value
      };

      try {
        const res = await API.updateActionItem(id, payload);
        const item = State.actionItems.find(a => a.id === id);
        if (item) Object.assign(item, res);
        renderActionItems();
        editModal.classList.remove('open');
        showToast('Action item updated successfully', 'success');
      } catch (err) {
        showToast('Failed to update action item', 'error');
      }
    });
  }

  // Node details modal close
  const nodeModal = document.getElementById('nodeDetailsModal');
  const btnCloseNode = document.getElementById('btnCloseNodeModal');
  if (btnCloseNode && nodeModal) {
    btnCloseNode.addEventListener('click', () => nodeModal.classList.remove('open'));
  }

  // Attendance Modal Form & Controls
  const attModal = document.getElementById('editAttendanceModal');
  const btnCloseAtt = document.getElementById('btnCloseAttendanceModal');
  const btnCancelAtt = document.getElementById('btnCancelAttendance');
  const attForm = document.getElementById('attendanceForm');

  if (btnCloseAtt && attModal) btnCloseAtt.addEventListener('click', () => attModal.classList.remove('open'));
  if (btnCancelAtt && attModal) btnCancelAtt.addEventListener('click', () => attModal.classList.remove('open'));

  if (attForm) {
    attForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const pId = parseInt(document.getElementById('attParticipantId').value);
      const payload = {
        name: document.getElementById('attParticipantName').value,
        employee_id: document.getElementById('attEmployeeId').value,
        role: document.getElementById('attParticipantRole').value,
        join_time: document.getElementById('attJoinTime').value,
        leave_time: document.getElementById('attLeaveTime').value,
        is_verified: document.getElementById('attIsVerified').checked
      };

      try {
        await API.updateAttendance(State.currentMeetingId, pId, payload);
        showToast('Participant attendance updated', 'success');
        attModal.classList.remove('open');
        State.attendanceSummary = await API.getAttendance(State.currentMeetingId);
        renderAttendance();
        renderOverview();
      } catch (err) {
        showToast('Failed to save attendance: ' + err.message, 'error');
      }
    });
  }

  const btnOpenAddAtt = document.getElementById('btnOpenAddAttendanceModal');
  if (btnOpenAddAtt && attModal) {
    btnOpenAddAtt.addEventListener('click', () => {
      if (State.participants.length > 0) {
        window.openEditAttendanceModal(State.participants[0].id);
      } else {
        showToast('No participants available', 'error');
      }
    });
  }

  // Recurring Detail Modal Close
  const recModal = document.getElementById('recurringMeetingDetailModal');
  const btnCloseRec = document.getElementById('btnCloseRecurringModal');
  if (btnCloseRec && recModal) {
    btnCloseRec.addEventListener('click', () => recModal.classList.remove('open'));
  }

  // Meeting Plan Events
  const btnAddPart = document.getElementById('btnAddParticipantRow');
  if (btnAddPart) {
    btnAddPart.addEventListener('click', () => {
      addParticipantRowToPrep('', '', '', '');
    });
  }

  const btnSyncPrep = document.getElementById('btnLoadMeetingIntoPrep');
  if (btnSyncPrep) {
    btnSyncPrep.addEventListener('click', () => {
      if (!State.meeting) return;
      const topicInput = document.getElementById('planTopic');
      if (topicInput) topicInput.value = State.meeting.title;
      const durInput = document.getElementById('planDuration');
      if (durInput && State.meeting.duration) durInput.value = Math.round(State.meeting.duration / 60);

      const container = document.getElementById('planParticipantsContainer');
      if (container) {
        container.innerHTML = '';
        State.participants.forEach(p => {
          addParticipantRowToPrep(p.name, p.role || '', p.department || '', p.responsibilities || '');
        });
      }
      showToast('Synchronized form with active meeting data', 'info');
    });
  }

  const planForm = document.getElementById('meetingPlanForm');
  if (planForm) {
    planForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const pRows = document.querySelectorAll('.plan-participant-row');
      const participantsData = [];
      pRows.forEach(row => {
        participantsData.push({
          name: row.querySelector('.row-p-name').value,
          role: row.querySelector('.row-p-role').value,
          department: row.querySelector('.row-p-dept').value,
          responsibilities: row.querySelector('.row-p-resp').value
        });
      });

      const payload = {
        meeting_topic: document.getElementById('planTopic').value,
        objective: document.getElementById('planObjective').value,
        duration_minutes: parseInt(document.getElementById('planDuration').value) || 45,
        meeting_type: document.getElementById('planMeetingType').value,
        department: document.getElementById('planDepartment').value,
        industry_context: document.getElementById('planIndustry').value,
        participants: participantsData
      };

      showToast('Generating AI expected conversation plan...', 'info');
      try {
        const plan = await API.generateMeetingPlan(State.currentMeetingId, payload);
        displayGeneratedMeetingPlan(plan);
        showToast('Expected conversation plan generated!', 'success');
      } catch (err) {
        showToast('Failed to generate meeting plan: ' + err.message, 'error');
      }
    });
  }

  const btnSavePlan = document.getElementById('btnSaveMeetingPlan');
  if (btnSavePlan) {
    btnSavePlan.addEventListener('click', async () => {
      if (!State.generatedPlanDraft) {
        showToast('Please generate a plan first', 'error');
        return;
      }
      try {
        await API.saveMeetingPlan(State.currentMeetingId, State.generatedPlanDraft);
        State.meetingPlan = State.generatedPlanDraft;
        State.topicCoverage = await API.getTopicCoverage(State.currentMeetingId);
        State.roleContributions = await API.getRoleContributions(State.currentMeetingId);
        renderExpectedVsActual();
        renderOverview();
        showToast('Meeting plan saved and topic coverage recalculated!', 'success');
      } catch (err) {
        showToast('Failed to save meeting plan: ' + err.message, 'error');
      }
    });
  }

  const btnStartAnalysis = document.getElementById('btnStartAnalysisFromPlan');
  if (btnStartAnalysis) {
    btnStartAnalysis.addEventListener('click', () => {
      const expTabBtn = document.querySelector('[data-tab="expected-vs-actual"]');
      if (expTabBtn) expTabBtn.click();
    });
  }

  // Recurring filter buttons setup
  const recFilterBtns = document.querySelectorAll('#recurringFilterButtons button');
  recFilterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const filter = btn.getAttribute('data-filter');
      renderRecurringTopics(filter);
    });
  });

  // Seed Demo Button
  const btnSeed = document.getElementById('btnSeedDemo');
  if (btnSeed) {
    btnSeed.addEventListener('click', async () => {
      showToast('Seeding sprint sync demo...', 'info');
      await API.seedDemo();
      await loadMeetingsList();
      showToast('Demo meeting ready', 'success');
    });
  }

  // Compare Tab Button
  const btnCompareTab = document.querySelector('[data-tab="compare"]');
  if (btnCompareTab) {
    btnCompareTab.addEventListener('click', runComparison);
  }
  const btnRefreshComp = document.getElementById('btnRunComparison');
  if (btnRefreshComp) {
    btnRefreshComp.addEventListener('click', runComparison);
  }
}

// Setup Exports
function setupExports() {
  const btnJson = document.getElementById('btnExportJson');
  const btnCsv = document.getElementById('btnExportCsv');

  if (btnJson) {
    btnJson.addEventListener('click', () => {
      if (!State.currentMeetingId) return;
      window.open(`/api/meetings/${State.currentMeetingId}/export?format=json`, '_blank');
      showToast('Exported meeting intelligence as JSON', 'success');
    });
  }

  if (btnCsv) {
    btnCsv.addEventListener('click', () => {
      if (!State.currentMeetingId) return;
      window.open(`/api/meetings/${State.currentMeetingId}/export?format=csv`, '_blank');
      showToast('Exported meeting action items & metrics as CSV', 'success');
    });
  }
}

// ==========================================================================
// ADVANCED FEATURES RENDERERS (FEATURES 1 - 7)
// ==========================================================================

// ==================== FEATURE 2 & 3: MEETING PREPARATION RENDERER ====================
function renderPreparation() {
  const container = document.getElementById('planParticipantsContainer');
  if (!container) return;

  if (container.children.length === 0) {
    if (State.participants && State.participants.length > 0) {
      container.innerHTML = '';
      State.participants.forEach(p => {
        addParticipantRowToPrep(p.name, p.role || '', p.department || 'Product & Engineering', p.responsibilities || '');
      });
    } else {
      addParticipantRowToPrep('Alice', 'Project Manager', 'Product & Engineering', 'Project status, timeline, resource allocation, and risk management');
      addParticipantRowToPrep('Bob', 'Data Scientist', 'Machine Learning', 'Dataset curation, model latency, validation accuracy, and inference pipelines');
      addParticipantRowToPrep('Charlie', 'Backend Developer', 'Platform Engineering', 'High-throughput APIs, database indexing, concurrency bottlenecks, and cloud deployments');
      addParticipantRowToPrep('David', 'UI Developer', 'Frontend Experience', 'Design system components, responsive layouts, client state management, and accessibility');
      addParticipantRowToPrep('Emily', 'QA Engineer', 'Quality Assurance', 'End-to-end regression testing, automated test coverage, and test environments');
    }
  }

  if (State.meeting) {
    const topicInput = document.getElementById('planTopic');
    if (topicInput && !topicInput.value) topicInput.value = State.meeting.title;
    const durInput = document.getElementById('planDuration');
    if (durInput && State.meeting.duration) durInput.value = Math.round(State.meeting.duration / 60);
  }

  if (State.meetingPlan) {
    displayGeneratedMeetingPlan(State.meetingPlan);
  }
}

function addParticipantRowToPrep(name = '', role = '', dept = '', resp = '') {
  const container = document.getElementById('planParticipantsContainer');
  if (!container) return;

  const row = document.createElement('div');
  row.className = 'plan-participant-row';
  row.style.display = 'grid';
  row.style.gridTemplateColumns = '1.2fr 1.2fr 1fr 2fr auto';
  row.style.gap = '0.5rem';
  row.style.alignItems = 'center';

  row.innerHTML = `
    <input type="text" class="form-input row-p-name" placeholder="Name" value="${escapeHtml(name)}" required>
    <input type="text" class="form-input row-p-role" placeholder="Role (e.g. Backend Dev)" value="${escapeHtml(role)}" required>
    <input type="text" class="form-input row-p-dept" placeholder="Dept" value="${escapeHtml(dept)}">
    <input type="text" class="form-input row-p-resp" placeholder="Key Domain Responsibilities" value="${escapeHtml(resp)}">
    <button type="button" class="btn btn-secondary btn-sm btn-remove-row" style="color: #fb7185; padding: 0.4rem 0.6rem;">&times;</button>
  `;

  row.querySelector('.btn-remove-row').addEventListener('click', () => {
    row.remove();
  });

  container.appendChild(row);
}

function displayGeneratedMeetingPlan(plan) {
  State.generatedPlanDraft = plan;
  const outputContainer = document.getElementById('planOutputContainer');
  if (!outputContainer) return;
  outputContainer.style.display = 'block';

  // Suggested Agenda
  const agendaTbody = document.getElementById('planAgendaTableBody');
  if (agendaTbody && Array.isArray(plan.suggested_agenda)) {
    agendaTbody.innerHTML = plan.suggested_agenda.map(item => `
      <tr>
        <td><strong style="color: #818cf8; font-family: var(--font-mono);">${escapeHtml(item.time_window || item.time || '')}</strong></td>
        <td><strong>${escapeHtml(item.topic || '')}</strong></td>
        <td><span class="badge" style="background: rgba(99,102,241,0.15); color: #818cf8;">${escapeHtml(item.lead || 'Team')}</span></td>
        <td style="color: var(--text-secondary);">${escapeHtml(item.expected_outcome || item.outcome || '')}</td>
      </tr>
    `).join('');
  }

  // Expected Topics
  const topicsList = document.getElementById('planExpectedTopicsList');
  if (topicsList && Array.isArray(plan.expected_topics)) {
    topicsList.innerHTML = plan.expected_topics.map(t => `
      <li style="display: flex; align-items: flex-start; gap: 0.5rem;">
        <span style="color: #818cf8;">•</span>
        <span>${escapeHtml(t)}</span>
      </li>
    `).join('');
  }

  // Expected Questions
  const questionsList = document.getElementById('planExpectedQuestionsList');
  if (questionsList && Array.isArray(plan.expected_questions)) {
    questionsList.innerHTML = plan.expected_questions.map(q => `
      <li style="display: flex; align-items: flex-start; gap: 0.5rem;">
        <span style="color: #22d3ee;">?</span>
        <span>${escapeHtml(q)}</span>
      </li>
    `).join('');
  }

  // Expected Decisions
  const decisionsList = document.getElementById('planExpectedDecisionsList');
  if (decisionsList && Array.isArray(plan.expected_decisions)) {
    decisionsList.innerHTML = plan.expected_decisions.map(d => `
      <li style="display: flex; align-items: flex-start; gap: 0.5rem;">
        <span style="color: #34d399;">✓</span>
        <span>${escapeHtml(d)}</span>
      </li>
    `).join('');
  }

  // Expected Action Areas
  const actionsList = document.getElementById('planExpectedActionsList');
  if (actionsList && Array.isArray(plan.expected_action_areas)) {
    actionsList.innerHTML = plan.expected_action_areas.map(a => `
      <li style="display: flex; align-items: flex-start; gap: 0.5rem;">
        <span style="color: #fbbf24;">→</span>
        <span>${escapeHtml(a)}</span>
      </li>
    `).join('');
  }

  // Role expectations grid
  const roleGrid = document.getElementById('planRoleExpectationsGrid');
  if (roleGrid && plan.role_expectations && typeof plan.role_expectations === 'object') {
    roleGrid.innerHTML = Object.entries(plan.role_expectations).map(([name, exp]) => {
      const topicsArr = Array.isArray(exp.expected_topics) ? exp.expected_topics : (Array.isArray(exp) ? exp : []);
      const roleStr = exp.role || 'Participant';
      return `
        <div class="glass-panel" style="padding: 1rem; background: rgba(0,0,0,0.25);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <strong style="color: #fff; font-size: 0.95rem;">${escapeHtml(name)}</strong>
            <span class="role-badge">${escapeHtml(roleStr)}</span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">Expected Domain Contributions:</div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.35rem;">
            ${topicsArr.map(t => `<span class="badge" style="background: rgba(192, 132, 252, 0.12); color: #c084fc; font-size: 0.72rem;">${escapeHtml(t)}</span>`).join('')}
          </div>
        </div>
      `;
    }).join('');
  }
}

// ==================== FEATURE 1: ATTENDANCE RENDERER ====================
function renderAttendance() {
  if (!State.attendanceSummary) return;
  const s = State.attendanceSummary;

  const elRate = document.getElementById('attSummaryRate');
  if (elRate) elRate.textContent = `${s.average_attendance_percentage}%`;
  const elOnTime = document.getElementById('attSummaryOnTime');
  if (elOnTime) elOnTime.textContent = s.on_time_count;
  const elLate = document.getElementById('attSummaryLate');
  if (elLate) elLate.textContent = s.late_arrivals_count;
  const elEarly = document.getElementById('attSummaryEarlyLeave');
  if (elEarly) elEarly.textContent = s.early_departures_count;
  const elVer = document.getElementById('attSummaryVerified');
  if (elVer) elVer.textContent = `${s.verified_count} / ${s.estimated_count}`;

  const elDur = document.getElementById('attMeetingDurationBadge');
  if (elDur) elDur.textContent = `${Math.round(s.meeting_total_duration_minutes)}m Total Duration`;

  // Render Chart
  renderAttendanceChart(s.records);

  // Render Presence Timeline
  renderAttendancePresenceTimeline(s.records, s.meeting_total_duration_minutes);

  // Render Detailed Table
  renderAttendanceTable(s.records);
}

function renderAttendanceChart(records) {
  const ctx = document.getElementById('attendanceChart');
  if (!ctx || !records) return;

  if (State.attendanceChart) {
    State.attendanceChart.destroy();
  }

  const labels = records.map(r => r.name);
  const data = records.map(r => r.attendance_percentage);
  const bgColors = records.map(r => {
    if (r.status === 'On time') return '#34d399';
    if (r.status === 'Late') return '#fb7185';
    if (r.status === 'Left early') return '#fbbf24';
    return '#818cf8';
  });

  State.attendanceChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Attendance %',
        data: data,
        backgroundColor: bgColors,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', callback: v => `${v}%` }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#f8fafc', font: { weight: '600' } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` Attendance: ${ctx.raw}% (${records[ctx.dataIndex]?.attendance_duration_minutes} min)`
          }
        }
      }
    }
  });
}

function renderAttendancePresenceTimeline(records, totalMinutes) {
  const container = document.getElementById('attendanceTimelineContainer');
  if (!container || !records) return;

  if (totalMinutes <= 0) totalMinutes = 45;

  container.innerHTML = records.map(r => {
    const joinM = r.join_time_minutes || 0;
    const leaveM = r.leave_time_minutes || totalMinutes;
    const leftPct = Math.max(0, Math.min(100, (joinM / totalMinutes) * 100));
    const widthPct = Math.max(5, Math.min(100 - leftPct, ((leaveM - joinM) / totalMinutes) * 100));

    let barClass = 'on-time';
    if (r.status === 'Late') barClass = 'late';
    else if (r.status === 'Left early') barClass = 'early-leave';

    return `
      <div class="presence-timeline-row">
        <div class="presence-participant-label" title="${escapeHtml(r.name)} (${escapeHtml(r.role || '')})">
          ${escapeHtml(r.name)}
        </div>
        <div class="presence-track" title="${r.join_time} - ${r.leave_time} (${r.attendance_duration_minutes} min)">
          <div class="presence-bar ${barClass}" style="left: ${leftPct}%; width: ${widthPct}%;"></div>
        </div>
        <div style="font-size: 0.72rem; color: var(--text-muted); width: 45px; text-align: right;">
          ${r.attendance_percentage}%
        </div>
      </div>
    `;
  }).join('');
}

function renderAttendanceTable(records) {
  const tbody = document.getElementById('attendanceTableBody');
  if (!tbody || !records) return;

  tbody.innerHTML = records.map(r => {
    let statusBadge = `<span class="badge-on-time">On time</span>`;
    if (r.status === 'Late') {
      statusBadge = `<span class="badge-late">Late (+${r.late_arrival_minutes}m)</span>`;
    } else if (r.status === 'Left early') {
      statusBadge = `<span class="badge-early-leave">Left early (-${r.early_leaving_minutes}m)</span>`;
    } else if (r.status === 'Partial attendance') {
      statusBadge = `<span class="badge-partial">Partial</span>`;
    }

    const sourceBadge = r.is_verified
      ? `<span class="badge-verified">✓ Verified attendance</span>`
      : `<span class="badge-estimated">~ Estimated from transcript</span>`;

    const bounds = (r.first_appearance_transcript || r.last_appearance_transcript)
      ? `${r.first_appearance_transcript || '00:00'} → ${r.last_appearance_transcript || '-'}`
      : 'N/A';

    return `
      <tr>
        <td><strong style="color: #fff;">${escapeHtml(r.name)}</strong></td>
        <td><span style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(r.employee_id || '-')}</span></td>
        <td><span class="role-badge">${escapeHtml(r.role || 'Member')}</span></td>
        <td><span style="font-family: var(--font-mono);">${escapeHtml(r.join_time)}</span></td>
        <td><span style="font-family: var(--font-mono);">${escapeHtml(r.leave_time)}</span></td>
        <td>${r.attendance_duration_minutes} min</td>
        <td><strong style="color: ${r.attendance_percentage >= 90 ? '#34d399' : (r.attendance_percentage >= 70 ? '#fbbf24' : '#fb7185')};">${r.attendance_percentage}%</strong></td>
        <td>${statusBadge}</td>
        <td>${sourceBadge}</td>
        <td><span style="font-size: 0.78rem; color: var(--text-secondary); font-family: var(--font-mono);">${bounds}</span></td>
        <td style="text-align: right;">
          <button class="btn btn-secondary btn-sm" onclick="window.openEditAttendanceModal(${r.participant_id})">Edit</button>
        </td>
      </tr>
    `;
  }).join('');
}

// ==================== FEATURE 4: TOPIC COVERAGE & FEATURE 3: ROLE CONTRIBUTION ====================
function renderExpectedVsActual() {
  renderTopicCoverage();
  renderRoleContributions();
}

function renderTopicCoverage() {
  if (!State.topicCoverage) return;
  const cov = State.topicCoverage;

  const elPct = document.getElementById('topicCoveragePercentageBadge');
  if (elPct) elPct.textContent = `${cov.coverage_percentage}%`;

  const elBar = document.getElementById('topicCoverageBarText');
  if (elBar) elBar.textContent = cov.progress_bar || `████████░░ ${cov.coverage_percentage}%`;

  const elReason = document.getElementById('topicCoverageReason');
  if (elReason) elReason.textContent = cov.reason || `Calculated based on semantic comparison against transcript deliberations.`;

  const elCov = document.getElementById('covCoveredCount');
  if (elCov) elCov.textContent = cov.covered_count;

  const elPart = document.getElementById('covPartialCount');
  if (elPart) elPart.textContent = cov.partially_covered_count;

  const elMiss = document.getElementById('covMissingCount');
  if (elMiss) elMiss.textContent = cov.not_discussed_count;

  const tbody = document.getElementById('topicCoverageTableBody');
  if (!tbody || !cov.topics) return;

  tbody.innerHTML = cov.topics.map(t => {
    let statusBadge = `<span class="badge-covered">✓ Covered</span>`;
    if (t.coverage_status === 'Partially Covered') {
      statusBadge = `<span class="badge-partial-cov">~ Partially Covered</span>`;
    } else if (t.coverage_status === 'Not Discussed') {
      statusBadge = `<span class="badge-missing">✗ Not Discussed</span>`;
    }

    const dur = t.discussion_duration_minutes > 0 ? `${t.discussion_duration_minutes} min` : '-';
    const matched = t.matched_transcript_topic ? `<strong>${escapeHtml(t.matched_transcript_topic)}</strong>` : '<span style="color: var(--text-muted);">No match</span>';

    return `
      <tr>
        <td><strong style="color: #fff;">${escapeHtml(t.expected_topic)}</strong></td>
        <td>${statusBadge}</td>
        <td><span style="font-family: var(--font-mono);">${dur}</span></td>
        <td>${matched}</td>
        <td style="font-size: 0.82rem; color: var(--text-secondary);">${escapeHtml(t.evidence_excerpt || 'No transcript discussion evidence detected for this topic.')}</td>
      </tr>
    `;
  }).join('');
}

function renderRoleContributions() {
  const container = document.getElementById('roleContributionsContainer');
  if (!container || !State.roleContributions || !State.roleContributions.contributions) return;

  container.innerHTML = State.roleContributions.contributions.map(c => {
    const expTopics = Array.isArray(c.expected_topics) ? c.expected_topics : [];
    const discTopics = Array.isArray(c.actually_discussed_topics) ? c.actually_discussed_topics : [];

    return `
      <div class="role-contrib-card">
        <div class="role-contrib-header">
          <div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${escapeHtml(c.name)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(c.department || '')}</div>
          </div>
          <span class="role-badge">${escapeHtml(c.role || 'Member')}</span>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.8rem; color: var(--text-secondary);">Topic Coverage</span>
          <strong style="color: #c084fc; font-size: 1.1rem;">${c.coverage_percentage}%</strong>
        </div>

        <div class="role-metric-row">
          <div class="role-metric-item">
            <div class="val">${c.speaking_percentage}%</div>
            <div class="lbl">Speaking</div>
          </div>
          <div class="role-metric-item">
            <div class="val">${c.questions_asked}</div>
            <div class="lbl">Questions</div>
          </div>
          <div class="role-metric-item">
            <div class="val">${c.ideas_contributed}</div>
            <div class="lbl">Ideas</div>
          </div>
          <div class="role-metric-item">
            <div class="val">${c.action_items_assigned}</div>
            <div class="lbl">Actions</div>
          </div>
        </div>

        <div>
          <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.35rem; text-transform: uppercase;">Expected Topics:</div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.3rem;">
            ${expTopics.map(t => `<span class="badge" style="background: rgba(192, 132, 252, 0.12); color: #c084fc; font-size: 0.7rem;">${escapeHtml(t)}</span>`).join('')}
          </div>
        </div>

        <div>
          <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.35rem; text-transform: uppercase;">Actually Discussed:</div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.3rem;">
            ${discTopics.length > 0 ? discTopics.map(t => `<span class="badge" style="background: rgba(52, 211, 153, 0.12); color: #34d399; font-size: 0.7rem;">✓ ${escapeHtml(t)}</span>`).join('') : '<span style="font-size: 0.75rem; color: var(--text-muted);">None observed</span>'}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ==================== FEATURE 5: AGENDA DRIFT DETECTOR ====================
function renderAgendaDrift() {
  if (!State.agendaDrift) return;
  const d = State.agendaDrift;

  const elInc = document.getElementById('driftStatIncidents');
  if (elInc) elInc.textContent = d.drift_count;
  const elDur = document.getElementById('driftStatDuration');
  if (elDur) elDur.textContent = `${d.total_drift_minutes} min`;
  const elPct = document.getElementById('driftStatPercentage');
  if (elPct) elPct.textContent = `${d.drift_percentage}%`;
  const elDisc = document.getElementById('driftStatDiscipline');
  if (elDisc) elDisc.textContent = `${d.agenda_alignment_percentage}%`;

  // Render Visual Timeline
  renderAgendaDriftTimeline(d);

  // Render Incident Cards
  renderAgendaDriftCards(d.drifts);
}

function renderAgendaDriftTimeline(driftData) {
  const container = document.getElementById('agendaDriftTimeline');
  if (!container || !driftData) return;

  const totalMin = driftData.meeting_duration_minutes || 45;
  const drifts = driftData.drifts || [];

  if (drifts.length === 0) {
    container.innerHTML = `
      <div class="drift-timeline-segment on-agenda" style="width: 100%;">
        100% On Agenda (00:00 - ${formatTime(totalMin * 60)})
      </div>
    `;
    return;
  }

  let html = '';
  let cursorMin = 0;

  drifts.forEach(drift => {
    const startM = drift.start_time_seconds / 60;
    const endM = drift.end_time_seconds / 60;

    if (startM > cursorMin) {
      const onAgendaDur = startM - cursorMin;
      const widthPct = (onAgendaDur / totalMin) * 100;
      html += `
        <div class="drift-timeline-segment on-agenda" style="width: ${widthPct}%;" title="On Agenda: ${formatTime(cursorMin * 60)} - ${formatTime(startM * 60)}">
          ${Math.round(onAgendaDur)}m On Agenda
        </div>
      `;
    }

    const driftDur = endM - startM;
    const driftWidthPct = (driftDur / totalMin) * 100;
    html += `
      <div class="drift-timeline-segment drift" style="width: ${driftWidthPct}%;" title="Potential Agenda Drift: ${escapeHtml(drift.detected_off_topic)} (${drift.start_time} - ${drift.end_time})">
        ⚠️ Drift (${Math.round(driftDur)}m)
      </div>
    `;

    cursorMin = endM;
  });

  if (cursorMin < totalMin) {
    const remDur = totalMin - cursorMin;
    const remWidthPct = (remDur / totalMin) * 100;
    html += `
      <div class="drift-timeline-segment on-agenda" style="width: ${remWidthPct}%;" title="On Agenda: ${formatTime(cursorMin * 60)} - ${formatTime(totalMin * 60)}">
        ${Math.round(remDur)}m On Agenda
      </div>
    `;
  }

  container.innerHTML = html;
}

function renderAgendaDriftCards(drifts) {
  const container = document.getElementById('agendaDriftsContainer');
  if (!container) return;

  if (!drifts || drifts.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
        <p>No agenda drifts detected. Conversation remained aligned with planned meeting topics.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = drifts.map(drift => {
    let categoryBadge = `<span class="badge-late">${escapeHtml(drift.severity_category)}</span>`;
    if (drift.severity_category === 'Minor Drift') {
      categoryBadge = `<span class="badge-partial-cov">${escapeHtml(drift.severity_category)}</span>`;
    }

    const confPct = Math.round((drift.confidence || 0.8) * 100);

    const feedbackStatus = drift.user_feedback_status || 'Pending Review';
    let feedbackBadge = `<span class="badge" style="background: rgba(255,255,255,0.06); color: var(--text-muted);">${escapeHtml(feedbackStatus)}</span>`;
    if (feedbackStatus === 'Confirmed Drift') {
      feedbackBadge = `<span class="badge-late">✓ Confirmed Drift</span>`;
    } else if (feedbackStatus === 'Disputed (On Agenda)') {
      feedbackBadge = `<span class="badge-covered">✓ Marked On-Agenda</span>`;
    }

    return `
      <div class="drift-card">
        <div class="drift-card-header">
          <div>
            <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.25rem;">
              <strong style="color: #fff; font-size: 1.05rem;">${escapeHtml(drift.detected_off_topic)}</strong>
              ${categoryBadge}
              ${feedbackBadge}
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              Expected Topic: <span style="color: #818cf8;">${escapeHtml(drift.expected_topic || 'Scheduled Agenda')}</span> • Duration: <strong>${drift.duration_minutes} min</strong> (${drift.start_time} - ${drift.end_time}) • Confidence: <strong>${confPct}%</strong>
            </div>
          </div>
        </div>

        <div class="drift-excerpt-box">
          "${escapeHtml(drift.transcript_excerpt || '')}"
        </div>

        <div class="drift-actions">
          <span style="font-size: 0.78rem; color: var(--text-muted); margin-right: 0.5rem;">User Verification:</span>
          <button class="btn btn-secondary btn-sm" onclick="window.handleDriftFeedback(${drift.id}, 'Confirmed Drift')">Confirm Drift</button>
          <button class="btn btn-secondary btn-sm" onclick="window.handleDriftFeedback(${drift.id}, 'Disputed (On Agenda)')">Not Drift</button>
        </div>
      </div>
    `;
  }).join('');
}

// ==================== FEATURE 6: PARTICIPATION GAPS RENDERER ====================
function renderParticipationGaps() {
  const container = document.getElementById('participationGapsContainer');
  const badgeCount = document.getElementById('badgeParticipationGapsCount');
  if (!container) return;

  if (!State.participationGaps || !State.participationGaps.gaps || State.participationGaps.gaps.length === 0) {
    if (badgeCount) badgeCount.textContent = '0 Gaps Detected';
    container.innerHTML = `
      <div style="grid-column: 1 / -1; background: rgba(52, 211, 153, 0.06); border: 1px solid rgba(52, 211, 153, 0.2); padding: 1rem; border-radius: var(--radius-md); color: var(--text-secondary); font-size: 0.85rem;">
        <span style="color: #34d399; font-weight: 600;">✓ Balanced Observed Participation:</span> All participants demonstrated active dialogue contributions consistent with meeting norms.
      </div>
    `;
    return;
  }

  const gaps = State.participationGaps.gaps;
  if (badgeCount) badgeCount.textContent = `${gaps.length} Gaps Detected`;

  container.innerHTML = gaps.map(g => {
    return `
      <div class="gap-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${escapeHtml(g.name)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(g.role || 'Participant')}</div>
          </div>
          <span class="badge" style="background: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.3);">
            Low Observed Participation
          </span>
        </div>

        <div class="role-metric-row">
          <div class="role-metric-item">
            <div class="val" style="color: #fbbf24;">${g.speaking_percentage}%</div>
            <div class="lbl">Speaking Share</div>
          </div>
          <div class="role-metric-item">
            <div class="val">${formatTime(g.speaking_time_seconds)}</div>
            <div class="lbl">Speaking Time</div>
          </div>
          <div class="role-metric-item">
            <div class="val">${g.turn_count}</div>
            <div class="lbl">Turns</div>
          </div>
          <div class="role-metric-item">
            <div class="val">${g.questions_count}</div>
            <div class="lbl">Questions</div>
          </div>
        </div>

        <p style="font-size: 0.82rem; color: var(--text-secondary); margin: 0; line-height: 1.45;">
          ${escapeHtml(g.explanation || '')}
        </p>

        <div class="gap-facilitation-box">
          <strong style="color: #818cf8; font-size: 0.78rem; text-transform: uppercase; display: block; margin-bottom: 0.2rem;">Facilitation Recommendation</strong>
          ${escapeHtml(g.facilitation_suggestion || '')}
        </div>
      </div>
    `;
  }).join('');
}

// ==================== FEATURE 7: RECURRING TOPICS RENDERER ====================
function renderRecurringTopics(filter = 'all') {
  if (!State.recurringTopics) return;
  State.activeRecurringFilter = filter;
  const r = State.recurringTopics;

  const elTot = document.getElementById('recStatTotal');
  if (elTot) elTot.textContent = r.total_recurring_count;
  const elUnres = document.getElementById('recStatUnresolved');
  if (elUnres) elUnres.textContent = r.unresolved_count;
  const elRes = document.getElementById('recStatResolved');
  if (elRes) elRes.textContent = r.resolved_count;

  // Update filter buttons
  const buttons = document.querySelectorAll('#recurringFilterButtons button');
  buttons.forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-filter') === filter);
  });

  let topics = r.recurring_topics || [];
  if (filter === 'unresolved') {
    topics = topics.filter(t => t.decision_status === 'Unresolved');
  } else if (filter === 'repeated') {
    topics = topics.filter(t => t.occurrences_count >= 2);
  } else if (filter === 'resolved') {
    topics = topics.filter(t => t.decision_status === 'Resolved');
  }

  const container = document.getElementById('recurringTopicsContainer');
  if (!container) return;

  if (topics.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
        <p>No recurring topics matching the "${escapeHtml(filter)}" filter.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = topics.map(t => {
    const statusBadge = t.decision_status === 'Resolved'
      ? `<span class="badge-covered">✓ Resolved</span>`
      : `<span class="badge-late">⚠️ Unresolved / Recurring</span>`;

    const occurrences = t.occurrences || [];

    return `
      <div class="recurring-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.25rem;">
              <strong style="color: #fff; font-size: 1.1rem;">${escapeHtml(t.topic_title)}</strong>
              ${statusBadge}
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              Discussed in <strong>${t.occurrences_count} meetings</strong> • First detected: <span style="color: #818cf8;">${escapeHtml(t.first_detected_meeting || 'Historical')}</span> • Last detected: <span style="color: #22d3ee;">${escapeHtml(t.last_detected_meeting || 'Current')}</span>
            </div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="window.openRecurringDetailModal('${escapeHtml(t.topic_title.replace(/'/g, "\\'"))}')">View Meetings</button>
        </div>

        <div class="recurring-trajectory-bar">
          ${occurrences.map((occ, idx) => `
            <div class="recurring-node-pill">
              <span style="font-weight: 700;">${escapeHtml(occ.meeting_title || `Meeting ${idx+1}`)}</span>
              <span style="color: var(--text-muted); font-size: 0.7rem;">(${occ.discussion_duration_minutes}m)</span>
            </div>
            ${idx < occurrences.length - 1 ? '<span class="recurring-arrow">───</span>' : ''}
          `).join('')}
        </div>

        ${t.latest_excerpt ? `
          <div style="background: rgba(0,0,0,0.25); border-left: 2px solid var(--accent-cyan); padding: 0.6rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.82rem; color: var(--text-secondary); font-style: italic;">
            "${escapeHtml(t.latest_excerpt)}"
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

// ==================== GLOBAL MODAL & ACTION HANDLERS ====================
window.openEditAttendanceModal = function(participantId) {
  if (!State.attendanceSummary || !State.attendanceSummary.records) return;
  const rec = State.attendanceSummary.records.find(r => r.participant_id === participantId);
  if (!rec) return;

  document.getElementById('attParticipantId').value = rec.participant_id;
  document.getElementById('attParticipantName').value = rec.name;
  document.getElementById('attEmployeeId').value = rec.employee_id || '';
  document.getElementById('attParticipantRole').value = rec.role || '';
  document.getElementById('attJoinTime').value = rec.join_time || '00:00';
  document.getElementById('attLeaveTime').value = rec.leave_time || '45:00';
  document.getElementById('attIsVerified').checked = rec.is_verified;

  const modal = document.getElementById('editAttendanceModal');
  if (modal) modal.classList.add('open');
};

window.openRecurringDetailModal = function(topicTitle) {
  if (!State.recurringTopics || !State.recurringTopics.recurring_topics) return;
  const rec = State.recurringTopics.recurring_topics.find(t => t.topic_title === topicTitle);
  if (!rec) return;

  const modal = document.getElementById('recurringMeetingDetailModal');
  const titleEl = document.getElementById('recurringModalTitle');
  const subtitleEl = document.getElementById('recurringModalSubtitle');
  const bodyEl = document.getElementById('recurringModalBody');
  if (!modal || !titleEl || !bodyEl) return;

  titleEl.textContent = `Recurring Topic: ${rec.topic_title}`;
  subtitleEl.textContent = `Discussed across ${rec.occurrences_count} recorded meetings (${rec.decision_status})`;

  bodyEl.innerHTML = (rec.occurrences || []).map((occ, idx) => `
    <div class="glass-panel" style="background: rgba(0,0,0,0.3); padding: 1.1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
        <div>
          <strong style="color: #22d3ee; font-size: 1rem;">${escapeHtml(occ.meeting_title || `Meeting ${idx+1}`)}</strong>
          <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;">Date: ${escapeHtml(occ.meeting_date || 'Historical')}</span>
        </div>
        <span class="badge" style="background: rgba(99,102,241,0.15); color: #818cf8;">${occ.discussion_duration_minutes} min duration</span>
      </div>
      <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
        Discussion Lead / Speakers: <strong>${escapeHtml(occ.lead_speaker || 'Team')}</strong>
      </div>
      <div class="drift-excerpt-box" style="border-left-color: var(--accent-cyan); color: #e2e8f0;">
        "${escapeHtml(occ.transcript_excerpt || 'Topic discussion recorded in session proceedings.')}"
      </div>
    </div>
  `).join('');

  modal.classList.add('open');
};

window.handleDriftFeedback = async function(driftId, feedbackStatus) {
  try {
    await API.submitDriftFeedback(State.currentMeetingId, driftId, feedbackStatus);
    showToast(`Feedback recorded: "${feedbackStatus}"`, 'success');
    if (State.agendaDrift && State.agendaDrift.drifts) {
      const d = State.agendaDrift.drifts.find(x => x.id === driftId);
      if (d) d.user_feedback_status = feedbackStatus;
      renderAgendaDriftCards(State.agendaDrift.drifts);
    }
  } catch (err) {
    showToast('Failed to record feedback: ' + err.message, 'error');
  }
};

