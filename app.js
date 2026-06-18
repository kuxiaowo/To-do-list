const { createApp } = Vue;
const TASKS_API = '/api/tasks';
const AUTH_API = '/api/auth';
const SCHEDULE_API = '/api/schedule-items';
const SCHEDULE_CONFIG_API = '/api/schedule-config';
const SCHEDULE_TEMPLATE_API = '/api/schedule-template';
const SCHEDULE_DAY_SLOTS_API = '/api/schedule-day-slots';
const HABITS_API = '/api/habits';
const ADMIN_API = '/api/admin';
const FEEDBACK_API = '/api/feedback';
const VISITS_API = '/api/visits';
const AI_CHAT_STREAM_API = '/api/ai/chat-stream';
const AUTH_TOKEN_KEY = 'todo-list-auth-token-v1';
const THEME_STORAGE_KEY = 'todo-list-theme-v1';
const GUIDE_STORAGE_KEY = 'todo-list-guide-v1';
const SIDEBAR_AUTO_COLLAPSE_WIDTH = 1100;
const DATE_RANGE_EXPAND_MARGIN = 21;
const HABIT_SYNC_FUTURE_DAYS = 90;
const AVATAR_SOURCE_MAX_BYTES = 8 * 1024 * 1024;
const AVATAR_UPLOAD_MAX_BYTES = 2 * 1024 * 1024;
const AVATAR_OUTPUT_SIZE = 512;
const AVATAR_CROP_SIZE = 260;
const AVATAR_ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const DEFAULT_AVATAR_COLOR = '#6366f1';
const AVATAR_QUICK_COLORS = [
  '#6366f1',
  '#0ea5e9',
  '#14b8a6',
  '#22c55e',
  '#f59e0b',
  '#ef4444',
  '#ec4899',
  '#8b5cf6',
  '#64748b'
];
// JavaScript Date months are zero-based, so 4 means May.
const TIMELINE_START_MONTH = 4;
const TIMELINE_START_DAY = 1;
const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 };
const PRIORITY_LABELS = { high: '高优先级', medium: '中优先级', low: '低优先级' };
const WEEKDAY_TEXT = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
const SUBJECT_TEMPLATE_API = '/api/subject-template';
const SUBJECT_TEMPLATE_EDIT_VALUE = '__edit_subject_template__';
const DEFAULT_SUBJECT_TEMPLATE = [
  'Chinese',
  'Mathematics',
  'English B',
  'IELTS',
  'Physics',
  'Economics',
  'Chemistry',
  'Psychology',
  'Biology',
  'Computer Science'
].map(name => ({ name, preset: true, enabled: true }));
const DEFAULT_WEEK_SLOTS = {
  0: [
    { keyBase: '0-09:00', label: '上午', start: '09:00', end: '10:00' },
    { keyBase: '1-10:00', label: '上午', start: '10:00', end: '11:00' },
    { keyBase: '2-11:00', label: '上午', start: '11:00', end: '12:00' },
    { keyBase: '3-14:00', label: '下午', start: '14:00', end: '15:00' },
    { keyBase: '4-15:00', label: '下午', start: '15:00', end: '16:00' },
    { keyBase: '5-17:00', label: '下午', start: '17:00', end: '18:00' },
    { keyBase: '6-18:00', label: '晚饭后', start: '18:00', end: '18:40' },
    { keyBase: '7-18:40', label: '第一节晚自习', start: '18:40', end: '19:40' },
    { keyBase: '8-19:50', label: '第二节晚自习', start: '19:50', end: '20:40' },
    { keyBase: '9-20:50', label: '第三节晚自习', start: '20:50', end: '21:30' },
  ],
  1: [
    { keyBase: '0-13:00', label: '午休', start: '13:00', end: '13:45' },
    { keyBase: '1-18:00', label: '晚饭后', start: '18:00', end: '18:40' },
    { keyBase: '2-18:40', label: '第一节晚自习', start: '18:40', end: '19:40' },
    { keyBase: '3-19:50', label: '第二节晚自习', start: '19:50', end: '20:40' },
    { keyBase: '4-20:50', label: '第三节晚自习', start: '20:50', end: '21:30' },
  ],
  2: [
    { keyBase: '0-13:00', label: '午休', start: '13:00', end: '13:45' },
    { keyBase: '1-18:00', label: '晚饭后', start: '18:00', end: '18:40' },
    { keyBase: '2-18:40', label: '第一节晚自习', start: '18:40', end: '19:40' },
    { keyBase: '3-19:50', label: '第二节晚自习', start: '19:50', end: '20:40' },
    { keyBase: '4-20:50', label: '第三节晚自习', start: '20:50', end: '21:30' },
  ],
  3: [
    { keyBase: '0-13:00', label: '午休', start: '13:00', end: '13:45' },
    { keyBase: '1-18:00', label: '晚饭后', start: '18:00', end: '18:40' },
    { keyBase: '2-18:40', label: '第一节晚自习', start: '18:40', end: '19:40' },
    { keyBase: '3-19:50', label: '第二节晚自习', start: '19:50', end: '20:40' },
    { keyBase: '4-20:50', label: '第三节晚自习', start: '20:50', end: '21:30' },
  ],
  4: [
    { keyBase: '0-13:00', label: '午休', start: '13:00', end: '13:45' },
    { keyBase: '1-18:00', label: '晚饭后', start: '18:00', end: '18:40' },
    { keyBase: '2-18:40', label: '第一节晚自习', start: '18:40', end: '19:40' },
    { keyBase: '3-19:50', label: '第二节晚自习', start: '19:50', end: '20:40' },
    { keyBase: '4-20:50', label: '第三节晚自习', start: '20:50', end: '21:30' },
  ],
  5: [
    { keyBase: '0-13:00', label: '午休', start: '13:00', end: '13:45' },
  ],
  6: [
    { keyBase: '0-09:00', label: '上午', start: '09:00', end: '10:00' },
    { keyBase: '1-10:00', label: '上午', start: '10:00', end: '11:00' },
    { keyBase: '2-11:00', label: '上午', start: '11:00', end: '12:00' },
    { keyBase: '3-14:00', label: '下午', start: '14:00', end: '15:00' },
    { keyBase: '4-15:00', label: '下午', start: '15:00', end: '16:00' },
    { keyBase: '5-17:00', label: '下午', start: '17:00', end: '18:00' },
    { keyBase: '6-19:00', label: '晚上', start: '19:00', end: '20:00' },
  ],
};

createApp({
  data() {
    return {
      tasks: [],
      scheduleItems: [],
      habits: [],
      aiChatOpen: false,
      aiChatMessages: [],
      aiChatInput: '',
      aiChatLoading: false,
      aiPendingActions: [],
      aiActionResults: [],
      aiApprovalVisible: false,
      aiCurrentActionIndex: 0,
      aiExecutingActionId: '',
      defaultWeekSlots: JSON.parse(JSON.stringify(DEFAULT_WEEK_SLOTS)),
      scheduleTemplateVersions: [],
      scheduleDayOverrides: {},
      sidebarCollapsed: typeof window !== 'undefined' && window.innerWidth <= SIDEBAR_AUTO_COLLAPSE_WIDTH,
      showCompleted: false,
      isDarkMode: (localStorage.getItem(THEME_STORAGE_KEY) || 'light') === 'dark',
      activePage: 'ddl',
      ddlViewMode: 'timeline',
      ddlCalendarMonthKey: '',
      pageViewDateKeys: { ddl: '', daily: '' },
      dialogVisible: false,
      dialogMode: 'create',
      createDialogType: 'task',
      activeTaskId: null,
      activeTaskPool: 'todo',
      currentViewDateKey: '',
      quickJumpDate: '',
      form: this.emptyForm(),
      dayRange: { past: 90, future: 90 },
      suppressTimelineAutoExpand: false,
      timelineAutoExpandTimer: null,
      habitDialogVisible: false,
      habitDialogMode: 'create',
      activeHabitId: '',
      habitForm: this.emptyHabitForm(),
      habitSyncConflicts: [],
      authToken: localStorage.getItem(AUTH_TOKEN_KEY) || '',
      currentUser: null,
      authMode: 'login',
      accountMenuOpen: false,
      draggedTaskId: null,
      draggedScheduleItemId: null,
      scheduleDropPosition: null,
      schedulePointerDrag: null,
      scheduleDragPreview: null,
      suppressNextScheduleClick: false,
      scheduleDialogVisible: false,
      scheduleDialogMode: 'create',
      activeScheduleItemId: null,
      activeScheduleTask: null,
      activeScheduleSlot: null,
      activeScheduleSortOrder: null,
      scheduleForm: this.emptyScheduleForm(),
      slotEditorVisible: false,
      slotEditorMode: 'day',
      slotEditorDate: '',
      slotEditorWeekday: '1',
      slotEditorSlots: [],
      slotEditorWeekSlots: JSON.parse(JSON.stringify(DEFAULT_WEEK_SLOTS)),
      loginForm: { nickname: '', password: '' },
      registerForm: { name: '', nickname: '', password: '' },
      nicknameDialogVisible: false,
      nicknameForm: { nickname: '' },
      passwordDialogVisible: false,
      passwordForm: { currentPassword: '', newPassword: '', confirmPassword: '' },
      avatarDialogVisible: false,
      avatarLoading: false,
      avatarSourceUrl: '',
      avatarSourceName: '',
      avatarSourceType: '',
      avatarImage: null,
      avatarCrop: {
        x: 0,
        y: 0,
        scale: 1,
        minScale: 1,
        maxScale: 4,
        dragging: false,
        pointerId: null,
        startX: 0,
        startY: 0,
        originX: 0,
        originY: 0
      },
      avatarPreviewUrl: '',
      avatarColorDraft: DEFAULT_AVATAR_COLOR,
      subjectTemplate: JSON.parse(JSON.stringify(DEFAULT_SUBJECT_TEMPLATE)),
      subjectTemplateDialogVisible: false,
      subjectTemplateDraft: [],
      newSubjectName: '',
      lastSubjectBeforeTemplateEdit: '',
      feedbackDialogVisible: false,
      feedbackForm: { content: '' },
      feedbackItems: [],
      feedbackLimitPerUser: 10,
      feedbackLoading: false,
      adminMode: false,
      adminSection: 'users',
      adminUsers: [],
      adminUsersPage: 1,
      adminUsersPageSize: 20,
      adminSelectedUserId: '',
      adminEditingUserId: '',
      adminEditingName: '',
      adminLogs: [],
      adminLogsTotal: 0,
      adminLogsPage: 1,
      adminLogsPageSize: 50,
      adminFeedback: [],
      adminFeedbackTotal: 0,
      adminFeedbackPage: 1,
      adminFeedbackPageSize: 50,
      adminFeedbackLimitDraft: 10,
      adminFeedbackReplyVisible: false,
      adminFeedbackActive: null,
      adminFeedbackReply: '',
      adminTrafficView: '7d',
      adminTrafficHoverPoint: null,
      adminTrafficRecentTotal: 0,
      adminTrafficRecentPage: 1,
      adminTrafficRecentPageSize: 50,
      adminTrafficViewOptions: [
        { value: '30d', label: '30天' },
        { value: '7d', label: '7天' },
        { value: '1d', label: '1天' },
        { value: '6h', label: '6小时' }
      ],
      adminTraffic: {
        seriesUnit: 'day',
        totalVisits: 0,
        todayVisits: 0,
        uniqueIps: 0,
        todayUniqueIps: 0,
        trendSeries: [],
        dailySeries: [],
        topIps: [],
        recentVisits: []
      },
      adminAiUsageView: '7d',
      adminAiUsageHoverPoint: null,
      adminAiUsageUsersTotal: 0,
      adminAiUsagePage: 1,
      adminAiUsagePageSize: 50,
      adminAiGlobalLimitDraft: {
        windowHours: 24,
        inputTokenLimit: 200000,
        outputTokenLimit: 50000
      },
      adminAiUserLimitDrafts: {},
      adminAiUsage: {
        seriesUnit: 'day',
        globalLimit: {
          windowHours: 24,
          inputTokenLimit: 200000,
          outputTokenLimit: 50000
        },
        totalPromptTokens: 0,
        totalCompletionTokens: 0,
        totalCalls: 0,
        todayPromptTokens: 0,
        todayCompletionTokens: 0,
        todayCalls: 0,
        trendSeries: [],
        users: []
      },
      adminLoading: false,
      adminTimelineLoadedUserId: '',
      guideVisible: false,
      guideStepIndex: 0,
      guideTargetBox: null,
      guidePopoverStyle: {},
      guideSteps: [
        {
          key: 'account',
          target: 'account',
          title: '先登录自己的账号',
          text: '登录后才能保存你的待办、每日安排和反馈记录。',
          page: null
        },
        {
          key: 'add-task',
          target: 'add-task',
          title: '从这里新增任务',
          text: '在这里新增带DDL或是弹性的任务安排。',
          page: 'ddl'
        },
        {
          key: 'task-pool',
          target: 'task-pool',
          title: '左侧是待安排任务池',
          text: '没有想好截止时间的任务会先放在这里，想好之后在设置截止时间也不迟。',
          page: 'ddl'
        },
        {
          key: 'page-nav',
          target: 'page-nav',
          title: '两个核心视图',
          text: 'DDL 日期时间线用于看截止日期，每日安排用于把任务拆到具体时间格子里执行。',
          page: null
        },
        {
          key: 'ddl-timeline',
          target: 'ddl-timeline',
          title: 'DDL 会按日期展开',
          text: '带截止时间的任务会自动落到对应日期列。可以用定位今天、快捷定位、后一周快速移动。',
          page: 'ddl'
        },
        {
          key: 'switch-daily',
          target: 'daily-tab',
          title: '切到每日安排',
          text: '请点击上方“每日安排”页签，进入每天的时间格子视图。',
          page: 'ddl',
          waitForPage: 'daily',
          allowTargetClick: true
        },
        {
          key: 'daily-tools',
          target: 'daily-tools',
          title: '每日安排使用时间格子',
          text: '你可以维护一周模板，也可以只编辑某一天的时间格子，让安排贴合当天节奏。',
          page: 'daily'
        },
        {
          key: 'flex-pool',
          target: 'task-pool',
          title: '临时任务池',
          text: '这里放临时、长期，没有 DDL的任务。把任务从这里拖到右侧某个时间格子，就会生成当天的一次学习安排。',
          page: 'daily'
        },
        {
          key: 'ddl-dock',
          target: 'ddl-dock',
          title: '把 DDL 拖进每天的计划',
          text: '每日安排底部会显示按时间排序的 DDL。可以拖到上方时间格子生成安排，也可以点击打开详情修改或标记完成。',
          page: 'daily'
        },
        {
          key: 'feedback',
          target: 'feedback',
          title: '遇到问题可以反馈',
          text: '这里可以提交使用问题或改进建议，并查看管理员回复。',
          page: null
        }
      ]
    };
  },
  computed: {
    currentGuideStep() {
      return this.guideSteps[this.guideStepIndex] || null;
    },
    guideStepLabel() {
      return `${this.guideStepIndex + 1} / ${this.guideSteps.length}`;
    },
    guideNextDisabled() {
      return !!(this.currentGuideStep && this.currentGuideStep.waitForPage && this.activePage !== this.currentGuideStep.waitForPage);
    },
    guideNextText() {
      if (this.guideNextDisabled) return '请先点击页签';
      return this.guideStepIndex === this.guideSteps.length - 1 ? '完成' : '下一步';
    },
    isAdmin() {
      return this.currentUser && this.currentUser.role === 'admin';
    },
    selectedAdminUser() {
      const id = Number(this.adminSelectedUserId);
      return this.adminUsers.find(user => Number(user.id) === id) || null;
    },
    adminUserOptions() {
      return this.adminUsers.map(user => ({
        ...user,
        label: `${user.name}（${user.nickname}）`
      }));
    },
    paginatedAdminUsers() {
      const start = (this.adminUsersPage - 1) * this.adminUsersPageSize;
      return this.adminUsers.slice(start, start + this.adminUsersPageSize);
    },
    trafficMetricCards() {
      return [
        { label: '总访问', value: this.adminTraffic.totalVisits },
        { label: '今日访问', value: this.adminTraffic.todayVisits },
        { label: '独立 IP', value: this.adminTraffic.uniqueIps },
        { label: '今日独立 IP', value: this.adminTraffic.todayUniqueIps }
      ];
    },
    trafficSeries() {
      const series = Array.isArray(this.adminTraffic.trendSeries)
        ? this.adminTraffic.trendSeries
        : this.adminTraffic.dailySeries;
      return Array.isArray(series) ? series : [];
    },
    trafficChartTitle() {
      const labels = {
        '30d': '近 30 天访问趋势',
        '7d': '近 7 天访问趋势',
        '1d': '近 24 小时访问趋势',
        '6h': '近 6 小时访问趋势'
      };
      return labels[this.adminTrafficView] || '访问趋势';
    },
    trafficTopIpTitle() {
      const labels = {
        '30d': '近 30 天 Top IP',
        '7d': '近 7 天 Top IP',
        '1d': '近 24 小时 Top IP',
        '6h': '近 6 小时 Top IP'
      };
      return labels[this.adminTrafficView] || 'Top IP';
    },
    trafficChartPoints() {
      const series = this.trafficSeries;
      if (!series.length) return '';
      return this.trafficChartPointItems.map(point => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ');
    },
    trafficChartPointItems() {
      const series = this.trafficSeries;
      if (!series.length) return [];
      const maxVisits = Math.max(1, ...series.map(item => Number(item.visits || 0)));
      return series.map((item, index) => {
        const x = series.length === 1 ? 50 : (index / (series.length - 1)) * 100;
        const y = 92 - (Number(item.visits || 0) / maxVisits) * 76;
        return {
          ...item,
          x,
          y,
          visits: Number(item.visits || 0),
          uniqueIps: Number(item.uniqueIps || 0)
        };
      });
    },
    trafficChartLabels() {
      const series = this.trafficSeries;
      if (!series.length) return [];
      if (this.adminTrafficView === '6h' || this.adminTrafficView === '7d') return series;
      const step = this.adminTrafficView === '1d' ? 3 : 5;
      const labels = series.filter((item, index) => index % step === 0);
      const last = series[series.length - 1];
      if (labels[labels.length - 1] !== last) labels.push(last);
      return labels;
    },
    trafficMaxVisits() {
      const series = this.trafficSeries;
      return Math.max(0, ...series.map(item => Number(item.visits || 0)));
    },
    trafficHoverStyle() {
      if (!this.adminTrafficHoverPoint) return {};
      return {
        left: `${this.adminTrafficHoverPoint.x}%`,
        top: `${this.adminTrafficHoverPoint.y}%`
      };
    },
    aiUsageMetricCards() {
      return [
        { label: '全站输入 token', value: this.formatTokenCount(this.adminAiUsage.totalPromptTokens) },
        { label: '全站输出 token', value: this.formatTokenCount(this.adminAiUsage.totalCompletionTokens) },
        { label: '总调用次数', value: this.formatTokenCount(this.adminAiUsage.totalCalls) },
        { label: '今日输入 / 输出', value: `${this.formatTokenCount(this.adminAiUsage.todayPromptTokens)} / ${this.formatTokenCount(this.adminAiUsage.todayCompletionTokens)}` }
      ];
    },
    aiUsageSeries() {
      return Array.isArray(this.adminAiUsage.trendSeries) ? this.adminAiUsage.trendSeries : [];
    },
    aiUsageChartTitle() {
      const labels = {
        '30d': '近 30 天 Token 趋势',
        '7d': '近 7 天 Token 趋势',
        '1d': '近 24 小时 Token 趋势',
        '6h': '近 6 小时 Token 趋势'
      };
      return labels[this.adminAiUsageView] || 'Token 趋势';
    },
    aiUsageChartPointItems() {
      const series = this.aiUsageSeries;
      if (!series.length) return [];
      const maxTokens = Math.max(
        1,
        ...series.map(item => Number(item.promptTokens || 0)),
        ...series.map(item => Number(item.completionTokens || 0))
      );
      return series.map((item, index) => {
        const promptTokens = Number(item.promptTokens || 0);
        const completionTokens = Number(item.completionTokens || 0);
        const x = series.length === 1 ? 50 : (index / (series.length - 1)) * 100;
        const inputY = 92 - (promptTokens / maxTokens) * 76;
        const outputY = 92 - (completionTokens / maxTokens) * 76;
        return {
          ...item,
          x,
          y: Math.min(inputY, outputY),
          inputY,
          outputY,
          promptTokens,
          completionTokens,
          totalTokens: Number(item.totalTokens || 0),
          calls: Number(item.calls || 0)
        };
      });
    },
    aiUsageInputChartPoints() {
      if (!this.aiUsageChartPointItems.length) return '';
      return this.aiUsageChartPointItems.map(point => `${point.x.toFixed(2)},${point.inputY.toFixed(2)}`).join(' ');
    },
    aiUsageOutputChartPoints() {
      if (!this.aiUsageChartPointItems.length) return '';
      return this.aiUsageChartPointItems.map(point => `${point.x.toFixed(2)},${point.outputY.toFixed(2)}`).join(' ');
    },
    aiUsageChartLabels() {
      const series = this.aiUsageSeries;
      if (!series.length) return [];
      if (this.adminAiUsageView === '6h' || this.adminAiUsageView === '7d') return series;
      const step = this.adminAiUsageView === '1d' ? 3 : 5;
      const labels = series.filter((item, index) => index % step === 0);
      const last = series[series.length - 1];
      if (labels[labels.length - 1] !== last) labels.push(last);
      return labels;
    },
    aiUsageMaxTokens() {
      const series = this.aiUsageSeries;
      return Math.max(
        0,
        ...series.map(item => Number(item.promptTokens || 0)),
        ...series.map(item => Number(item.completionTokens || 0))
      );
    },
    aiUsageHoverStyle() {
      if (!this.adminAiUsageHoverPoint) return {};
      return {
        left: `${this.adminAiUsageHoverPoint.x}%`,
        top: `${this.adminAiUsageHoverPoint.y}%`
      };
    },
    sortedTasks() {
      return [...this.tasks].sort((a, b) => this.compareTasks(a, b));
    },
    filteredTasks() {
      return this.sortedTasks.filter(task => this.showCompleted || !task.completed);
    },
    todoTasksByDueDate() {
      return this.filteredTasks.reduce((groups, task) => {
        if (!task.dueAt || this.taskPool(task) !== 'todo') return groups;
        const key = String(task.dueAt).slice(0, 10);
        if (!groups[key]) groups[key] = [];
        groups[key].push(task);
        return groups;
      }, {});
    },
    unscheduledTasks() {
      return this.filteredTasks
        .filter(task => !task.dueAt && this.taskPool(task) === 'todo')
        .sort((a, b) => this.compareTasks(a, b));
    },
    arrangementTasks() {
      return this.filteredTasks
        .filter(task => !task.dueAt && this.taskPool(task) === 'arrangement')
        .sort((a, b) => this.compareTasks(a, b));
    },
    activePoolTasks() {
      return this.activePage === 'daily' ? this.arrangementTasks : this.unscheduledTasks;
    },
    unscheduledCount() {
      return this.activePoolTasks.length;
    },
    activeHabits() {
      return this.habits.filter(habit => !habit.archived);
    },
    activeHabit() {
      return this.activeHabits.find(habit => habit.id === this.activeHabitId) || null;
    },
    habitCount() {
      return this.activeHabits.length;
    },
    weekdayOptions() {
      return WEEKDAY_TEXT.map((label, value) => ({ label, value }));
    },
    habitSlotOptions() {
      const dateKey = this.habitForm.startDate || this.currentViewDateKey || this.formatDateKey(new Date());
      const weekdays = Array.isArray(this.habitForm.weekdays) ? this.habitForm.weekdays : [];
      if (weekdays.length) {
        const weekSlots = this.weekTemplateForDate(dateKey);
        let sharedSlots = null;
        weekdays.forEach((weekday) => {
          const slots = this.sortSlots(this.cloneSlots(weekSlots[String(weekday)] || []));
          if (sharedSlots === null) {
            sharedSlots = slots;
            return;
          }
          sharedSlots = sharedSlots.filter(slot => slots.some(item =>
            item.keyBase === slot.keyBase && item.start === slot.start && item.end === slot.end
          ));
        });
        return (sharedSlots || []).map(slot => ({
          ...slot,
          key: slot.keyBase,
          duration: this.minutesBetween(slot.start, slot.end),
          labelText: `${slot.label} ${slot.start}-${slot.end}`
        }));
      }
      return this.slotsForDate(dateKey).map(slot => ({
        ...slot,
        key: slot.keyBase,
        duration: this.minutesBetween(slot.start, slot.end),
        labelText: `${slot.label} ${slot.start}-${slot.end}`
      }));
    },
    habitSelectedSlotDuration() {
      const slot = this.habitSlotOptions.find(item => item.keyBase === this.habitForm.slotKeyBase);
      return slot ? slot.duration : 999;
    },
    activeScheduleIsHabit() {
      if (!this.activeScheduleItemId) return false;
      const item = this.scheduleItems.find(entry => entry.id === this.activeScheduleItemId);
      return !!(item && item.habitId);
    },
    isDirectScheduleCreate() {
      return this.scheduleDialogMode === 'create' && !this.activeScheduleTask;
    },
    directScheduleSlotOptions() {
      const dateKey = this.scheduleForm.date || this.currentViewDateKey || this.formatDateKey(new Date());
      return this.slotsForDate(dateKey).map(slot => ({
        ...slot,
        key: this.scheduleSlotKeyFromBase(dateKey, slot.keyBase),
        duration: this.minutesBetween(slot.start, slot.end),
        labelText: `${slot.label} ${slot.start}-${slot.end}`
      }));
    },
    enabledSubjectOptions() {
      return this.subjectTemplate
        .filter(item => item.enabled)
        .map(item => item.name);
    },
    subjectTemplateEditValue() {
      return SUBJECT_TEMPLATE_EDIT_VALUE;
    },
    pendingFeedbackCount() {
      return this.feedbackItems.filter(item => item.status !== 'replied').length;
    },
    quickJumpMarkedDateKeys() {
      const keys = new Set();
      if (this.activePage === 'daily') {
        this.scheduleItems
          .filter(item => item.date && !item.habitId && (this.showCompleted || !item.completed))
          .forEach(item => keys.add(String(item.date).slice(0, 10)));
        return keys;
      }
      Object.keys(this.todoTasksByDueDate).forEach(key => keys.add(key));
      return keys;
    },
    dayColumns() {
      const base = this.startOfDay(new Date());
      const start = this.timelineStartDate();
      const end = this.addDays(base, this.dayRange.future);
      const days = [];
      for (let date = new Date(start); date <= end; date = this.addDays(date, 1)) {
        const offset = this.daysBetween(base, date);
        const key = this.formatDateKey(date);
        const tasks = this.todoTasksByDueDate[key] || [];
        days.push({
          key,
          label: this.formatDateLabel(date),
          subtitle: this.relativeLabel(offset),
          tasks
        });
      }
      return days;
    },
    ddlCalendarTitle() {
      const monthDate = this.parseDateKey(this.ddlCalendarMonthKey || this.currentViewDateKey || this.formatDateKey(new Date()));
      return `${monthDate.getFullYear()} 年 ${monthDate.getMonth() + 1} 月`;
    },
    ddlCalendarWeekdays() {
      return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    },
    ddlCalendarDays() {
      const monthDate = this.parseDateKey(this.ddlCalendarMonthKey || this.currentViewDateKey || this.formatDateKey(new Date()));
      const monthStart = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
      const monthEnd = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0);
      const gridStart = this.ddlCalendarWeekStartDate(monthStart);
      const gridEnd = this.addDays(this.ddlCalendarWeekStartDate(monthEnd), 6);
      const todayKey = this.formatDateKey(new Date());
      const selectedKey = this.pageViewDateKeys.ddl || this.currentViewDateKey || todayKey;
      const days = [];
      for (let date = new Date(gridStart); date <= gridEnd; date = this.addDays(date, 1)) {
        const key = this.formatDateKey(date);
        days.push({
          key,
          dayNumber: date.getDate(),
          isCurrentMonth: date.getMonth() === monthStart.getMonth(),
          isToday: key === todayKey,
          isSelected: key === selectedKey,
          tasks: this.ddlTasksForDate(key)
        });
      }
      return days;
    },
    avatarText() {
      if (!this.currentUser) return '登';
      const source = this.currentUser.nickname || this.currentUser.name || '?';
      return source.trim().slice(0, 1).toUpperCase();
    },
    avatarImageUrl() {
      return this.currentUser && this.currentUser.avatarUrl ? this.currentUser.avatarUrl : '';
    },
    avatarQuickColors() {
      return AVATAR_QUICK_COLORS;
    },
    avatarColor() {
      const color = this.currentUser && this.currentUser.avatarColor ? String(this.currentUser.avatarColor).toLowerCase() : '';
      return this.isValidHexColor(color) ? color : DEFAULT_AVATAR_COLOR;
    },
    avatarFallbackStyle() {
      return { background: this.avatarColor };
    },
    avatarDraftColor() {
      return this.isValidHexColor(this.avatarColorDraft) ? this.avatarColorDraft.toLowerCase() : this.avatarColor;
    },
    avatarDraftFallbackStyle() {
      return { background: this.avatarDraftColor };
    },
    avatarHasPendingColor() {
      return this.avatarDraftColor !== this.avatarColor;
    },
    avatarCanSave() {
      return !!this.avatarImage || this.avatarHasPendingColor;
    },
    avatarDraftRgb() {
      const color = this.avatarDraftColor.slice(1);
      return {
        r: parseInt(color.slice(0, 2), 16),
        g: parseInt(color.slice(2, 4), 16),
        b: parseInt(color.slice(4, 6), 16)
      };
    },
    avatarCropImageStyle() {
      if (!this.avatarImage) return {};
      const width = this.avatarImage.width * this.avatarCrop.scale;
      const height = this.avatarImage.height * this.avatarCrop.scale;
      return {
        width: `${width}px`,
        height: `${height}px`,
        transform: `translate(${this.avatarCrop.x}px, ${this.avatarCrop.y}px)`
      };
    },
    ddlTasks() {
      return this.sortedTasks.filter(task => task.dueAt && this.taskPool(task) === 'todo' && !task.completed);
    },
    isCreatingArrangement() {
      return this.dialogMode === 'create' && this.createDialogType === 'arrangement';
    },
    isArrangementDialog() {
      return this.isCreatingArrangement || (this.dialogMode === 'edit' && this.activeTaskPool === 'arrangement');
    },
    dueHour: {
      get() {
        return String(this.form.time || '').split(':')[0] || '';
      },
      set(value) {
        this.setDialogTimePart('hour', value);
      }
    },
    dueMinute: {
      get() {
        return String(this.form.time || '').split(':')[1] || '';
      },
      set(value) {
        this.setDialogTimePart('minute', value);
      }
    },
    scheduleItemsBySlot() {
      const groups = this.scheduleItems.reduce((result, item) => {
        const key = this.scheduleSlotKey(item.date, item.slotKey);
        if (!result[key]) result[key] = [];
        result[key].push(item);
        return result;
      }, {});
      Object.values(groups).forEach(items => items.sort((a, b) => this.compareScheduleItems(a, b)));
      return groups;
    },
    scheduleDayColumns() {
      const base = this.startOfDay(new Date());
      const start = this.timelineStartDate();
      const end = this.addDays(base, this.dayRange.future);
      const days = [];
      for (let date = new Date(start); date <= end; date = this.addDays(date, 1)) {
        const offset = this.daysBetween(base, date);
        const key = this.formatDateKey(date);
        const rawSlots = this.slotsForDate(key);
        days.push({
          key,
          label: this.formatDateLabel(date),
          subtitle: this.relativeLabel(offset),
          hasOverride: !!this.scheduleDayOverrides[key],
          slots: rawSlots.map((slot) => ({
            ...slot,
            key: this.scheduleSlotKeyFromBase(key, slot.keyBase),
            duration: this.minutesBetween(slot.start, slot.end)
          }))
        });
      }
      return days;
    }
  },
  async mounted() {
    this.applyTheme();
    this.currentViewDateKey = this.formatDateKey(new Date());
    this.pageViewDateKeys.ddl = this.currentViewDateKey;
    this.pageViewDateKeys.daily = this.currentViewDateKey;
    this.setDdlCalendarMonth(this.currentViewDateKey);
    document.addEventListener('click', this.closeAccountMenu);
    await this.loadCurrentUser();
    await this.loadSubjectTemplate();
    await this.loadScheduleConfig();
    await this.loadTasks();
    await this.loadHabits();
    await this.loadScheduleItems();
    window.addEventListener('resize', this.handleViewportResize);
    window.addEventListener('scroll', this.updateGuideTarget, true);
    this.$nextTick(() => {
      this.scrollToDate(this.currentViewDateKey, 'ddl', 'instant');
      this.maybeStartGuide();
    });
  },
  beforeUnmount() {
    document.removeEventListener('click', this.closeAccountMenu);
    window.removeEventListener('resize', this.handleViewportResize);
    window.removeEventListener('scroll', this.updateGuideTarget, true);
    if (this.timelineAutoExpandTimer) window.clearTimeout(this.timelineAutoExpandTimer);
    this.removeSchedulePointerListeners();
    document.body.classList.remove('is-schedule-touch-dragging');
    this.scheduleDragPreview = null;
  },
  methods: {
    applyTheme() {
      const theme = this.isDarkMode ? 'dark' : 'light';
      document.documentElement.dataset.theme = theme;
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    },
    setTheme(value) {
      this.isDarkMode = !!value;
      this.applyTheme();
    },
    closeAccountMenu() {
      this.accountMenuOpen = false;
    },
    handleViewportResize() {
      if (window.innerWidth <= SIDEBAR_AUTO_COLLAPSE_WIDTH) {
        this.sidebarCollapsed = true;
      }
      this.updateGuideTarget();
    },
    maybeStartGuide() {
      if (this.adminMode || localStorage.getItem(GUIDE_STORAGE_KEY) === 'done') return;
      this.startGuide(false);
    },
    startGuide(force = true) {
      if (this.adminMode) {
        if (force) ElementPlus.ElMessage.info('新手指引仅在普通待办页面可用。');
        return;
      }
      this.accountMenuOpen = false;
      this.guideStepIndex = 0;
      this.guideVisible = true;
      this.showGuideStep();
    },
    showGuideStep() {
      const step = this.currentGuideStep;
      if (!step) {
        this.finishGuide();
        return;
      }
      if (step.page && step.page !== this.activePage) {
        this.switchPage(step.page);
      }
      if (['add-task', 'task-pool'].includes(step.target)) {
        this.sidebarCollapsed = false;
      }
      this.$nextTick(() => {
        window.setTimeout(() => this.updateGuideTarget(), 80);
      });
    },
    nextGuideStep() {
      if (this.guideStepIndex >= this.guideSteps.length - 1) {
        this.finishGuide();
        return;
      }
      this.guideStepIndex += 1;
      this.showGuideStep();
    },
    prevGuideStep() {
      if (this.guideStepIndex <= 0) return;
      this.guideStepIndex -= 1;
      this.showGuideStep();
    },
    skipGuide() {
      this.finishGuide();
    },
    finishGuide() {
      this.guideVisible = false;
      this.guideTargetBox = null;
      this.guidePopoverStyle = {};
      localStorage.setItem(GUIDE_STORAGE_KEY, 'done');
    },
    updateGuideTarget() {
      if (!this.guideVisible || !this.currentGuideStep) return;
      const target = document.querySelector(`[data-guide="${this.currentGuideStep.target}"]`);
      if (!target) {
        this.guideTargetBox = null;
        this.guidePopoverStyle = {};
        return;
      }

      const rect = target.getBoundingClientRect();
      const padding = 8;
      const top = Math.max(8, rect.top - padding);
      const left = Math.max(8, rect.left - padding);
      const width = Math.min(window.innerWidth - left - 8, rect.width + padding * 2);
      const height = Math.min(window.innerHeight - top - 8, rect.height + padding * 2);
      this.guideTargetBox = {
        top: `${top}px`,
        left: `${left}px`,
        width: `${Math.max(44, width)}px`,
        height: `${Math.max(36, height)}px`
      };

      const popoverWidth = Math.min(340, window.innerWidth - 24);
      let popoverLeft = Math.min(window.innerWidth - popoverWidth - 12, Math.max(12, rect.left));
      let popoverTop = rect.bottom + 16;
      if (popoverTop + 220 > window.innerHeight) {
        popoverTop = Math.max(12, rect.top - 236);
      }
      if (window.innerWidth <= 720) {
        popoverLeft = 12;
        popoverTop = Math.max(12, Math.min(window.innerHeight - 230, rect.bottom + 12));
      }
      this.guidePopoverStyle = {
        top: `${popoverTop}px`,
        left: `${popoverLeft}px`,
        width: `${popoverWidth}px`
      };
    },
    emptyForm() {
      const now = new Date();
      return {
        title: '',
        subject: '',
        date: this.formatDateKey(now),
        time: this.pad(now.getHours()) + ':' + this.pad(now.getMinutes()),
        unscheduled: false,
        priority: 'medium',
        note: '',
        completed: false
      };
    },
    emptyHabitForm() {
      const today = this.formatDateKey(new Date());
      return {
        title: '',
        subject: '',
        weekdays: [],
        slotKeyBase: '',
        slotLabel: '',
        slotStart: '',
        slotEnd: '',
        durationMinutes: 30,
        startDate: today,
        endDate: '',
        priority: 'medium',
        note: '',
        active: true
      };
    },
    emptyScheduleForm() {
      const today = this.formatDateKey(new Date());
      return {
        title: '',
        subject: '',
        date: today,
        slotKeyBase: '',
        durationMinutes: 30,
        priority: 'medium',
        note: '',
        completed: false
      };
    },
    authHeaders() {
      return this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {};
    },
    async apiJson(url, options = {}) {
      // Centralized JSON fetch wrapper for authenticated API requests.
      const response = await fetch(url, {
        ...options,
        headers: {
          ...(options.body ? { 'Content-Type': 'application/json' } : {}),
          ...this.authHeaders(),
          ...(options.headers || {})
        }
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.message || payload.error || '请求失败');
      return payload;
    },
    toggleAiChat() {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再使用 AI 助手。');
        return;
      }
      this.aiChatOpen = !this.aiChatOpen;
      if (this.aiChatOpen) {
        this.$nextTick(() => {
          const input = this.$refs.aiChatInput;
          if (input && input.focus) input.focus();
          this.scrollAiChatToBottom();
        });
      }
    },
    scrollAiChatToBottom() {
      this.$nextTick(() => {
        const body = this.$refs.aiChatBody;
        if (body) body.scrollTop = body.scrollHeight;
      });
    },
    aiHistoryForRequest() {
      return this.aiChatMessages
        .slice(-20)
        .map(item => ({ role: item.role, content: item.content }))
        .filter(item => ['user', 'assistant'].includes(item.role) && item.content);
    },
    handleAiChatKeydown(event) {
      if (event.key !== 'Enter' || event.shiftKey) return;
      event.preventDefault();
      this.sendAiMessage();
    },
    setAiChatMessageContent(message, content) {
      const index = this.aiChatMessages.indexOf(message);
      const nextMessage = { ...message, content };
      if (index !== -1) {
        this.aiChatMessages.splice(index, 1, nextMessage);
        return nextMessage;
      }
      message.content = content;
      return message;
    },
    async readAiChatStream(body, onDelta) {
      const response = await fetch(AI_CHAT_STREAM_API, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders()
        },
        body: JSON.stringify(body)
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.message || payload.error || '请求失败');
      }
      if (!response.body) throw new Error('当前浏览器不支持流式响应');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let donePayload = null;

      const handleBlock = block => {
        const lines = block.split(/\r?\n/);
        let event = 'message';
        const dataLines = [];
        lines.forEach(line => {
          if (line.startsWith('event:')) {
            event = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trimStart());
          }
        });
        if (!dataLines.length) return;
        const payload = JSON.parse(dataLines.join('\n'));
        if (event === 'delta') {
          onDelta(String(payload.text || ''));
        } else if (event === 'done') {
          donePayload = payload;
        } else if (event === 'error') {
          throw new Error(payload.message || payload.error || 'AI 请求失败');
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundaryIndex = buffer.indexOf('\n\n');
        while (boundaryIndex !== -1) {
          const block = buffer.slice(0, boundaryIndex);
          buffer = buffer.slice(boundaryIndex + 2);
          if (block.trim()) handleBlock(block);
          if (donePayload) {
            await reader.cancel().catch(() => {});
            return donePayload;
          }
          boundaryIndex = buffer.indexOf('\n\n');
        }
      }
      buffer += decoder.decode();
      if (buffer.trim()) handleBlock(buffer);
      if (!donePayload) throw new Error('AI 流式响应没有结束标记');
      return donePayload;
    },
    aiRejectedSummary(rejected) {
      const reasons = (Array.isArray(rejected) ? rejected : [])
        .map(item => String(item.reason || '').trim())
        .filter(Boolean)
        .slice(0, 3);
      if (!reasons.length) return '有些候选操作没有通过校验，未写入任务。';
      return `有些候选操作没有通过校验，未写入任务。原因：${reasons.join('；')}`;
    },
    async sendAiMessage() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再使用 AI 助手。');
        return;
      }
      const message = this.aiChatInput.trim();
      if (!message || this.aiChatLoading) return;
      const history = this.aiHistoryForRequest();
      this.aiChatInput = '';
      this.aiChatMessages.push({ role: 'user', content: message });
      let assistantMessage = { role: 'assistant', content: '' };
      this.aiChatMessages.push(assistantMessage);
      this.aiChatLoading = true;
      this.scrollAiChatToBottom();
      try {
        const payload = await this.readAiChatStream({
          message,
          history,
          clientNow: new Date().toISOString(),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai'
        }, text => {
          if (!text) return;
          assistantMessage = this.setAiChatMessageContent(assistantMessage, assistantMessage.content + text);
          this.scrollAiChatToBottom();
        });
        const reply = payload.reply || '我没有生成可执行操作。';
        assistantMessage = this.setAiChatMessageContent(assistantMessage, reply);
        const actions = Array.isArray(payload.actions) ? payload.actions : [];
        if (actions.length) {
          this.openAiApproval(actions);
        }
        const rejected = Array.isArray(payload.rejectedActions) ? payload.rejectedActions : [];
        if (!actions.length && rejected.length) {
          this.aiChatMessages.push({ role: 'assistant', content: this.aiRejectedSummary(rejected) });
        }
      } catch (error) {
        console.error('AI 助手请求失败：', error);
        assistantMessage = this.setAiChatMessageContent(assistantMessage, `AI 请求失败：${error.message}`);
        ElementPlus.ElMessage.error(`AI 请求失败：${error.message}`);
      } finally {
        this.aiChatLoading = false;
        this.scrollAiChatToBottom();
      }
    },
    openAiApproval(actions) {
      this.aiPendingActions = actions.map(action => this.normalizeAiApprovalAction(action));
      this.aiActionResults = this.aiPendingActions.map(action => ({
        actionId: action.id,
        status: 'pending',
        message: ''
      }));
      this.aiCurrentActionIndex = 0;
      this.aiExecutingActionId = '';
      this.aiApprovalVisible = true;
    },
    normalizeAiApprovalAction(action) {
      const normalized = { ...action };
      if (normalized.type === 'create_task') {
        normalized.draft = {
          title: '',
          subject: '',
          dueAt: '',
          priority: 'medium',
          note: '',
          ...(normalized.task || {})
        };
      } else {
        normalized.draft = {
          title: '',
          subject: '',
          dueAt: '',
          priority: 'medium',
          note: '',
          ...(normalized.before || {}),
          ...(normalized.patch || {}),
          ...(normalized.after || {})
        };
      }
      return normalized;
    },
    currentAiAction() {
      return this.aiPendingActions[this.aiCurrentActionIndex] || null;
    },
    aiActionResult(action) {
      if (!action) return null;
      return this.aiActionResults.find(result => result.actionId === action.id) || null;
    },
    aiActionStatus(action) {
      const result = this.aiActionResult(action);
      return result ? result.status : 'pending';
    },
    aiActionStatusLabel(action) {
      const status = this.aiActionStatus(action);
      return {
        pending: '待处理',
        executed: '已执行',
        canceled: '已取消'
      }[status] || '待处理';
    },
    aiActionStatusType(action) {
      const status = this.aiActionStatus(action);
      return {
        pending: 'info',
        executed: 'success',
        canceled: 'warning'
      }[status] || 'info';
    },
    aiActionTypeLabel(action) {
      if (!action) return '';
      return action.type === 'create_task' ? '创建任务' : '修改任务';
    },
    aiEditableFields() {
      return ['title', 'subject', 'dueAt', 'priority', 'note'].map(field => ({
        field,
        label: this.aiFieldLabel(field)
      }));
    },
    aiActionLocked(action) {
      return ['executed', 'canceled'].includes(this.aiActionStatus(action));
    },
    aiActionFieldChanged(action, field) {
      if (!action || action.type !== 'update_task') return false;
      const before = action.before || {};
      const draft = action.draft || {};
      return String(before[field] || '') !== String(draft[field] || '');
    },
    aiFieldLabel(field) {
      return {
        title: '标题',
        subject: '科目',
        dueAt: '截止时间',
        priority: '优先级',
        note: '备注'
      }[field] || field;
    },
    aiFormatFieldValue(field, value) {
      if (field === 'priority') return this.priorityLabel(value || 'medium');
      if (field === 'dueAt') return value ? String(value).replace('T', ' ').slice(0, 16) : '无截止时间';
      return value === '' || value === null || value === undefined ? '空' : String(value);
    },
    aiActionPreviewFields(action) {
      if (!action) return [];
      if (action.type === 'create_task') {
        const task = action.task || {};
        return ['title', 'subject', 'dueAt', 'priority', 'note'].map(field => ({
          field,
          label: this.aiFieldLabel(field),
          mode: 'create',
          after: this.aiFormatFieldValue(field, task[field] || '')
        }));
      }
      const patch = action.patch || {};
      const before = action.before || {};
      return Object.keys(patch).map(field => ({
        field,
        label: this.aiFieldLabel(field),
        mode: 'update',
        before: this.aiFormatFieldValue(field, before[field] || ''),
        after: this.aiFormatFieldValue(field, patch[field] || '')
      }));
    },
    normalizeAiDraftFields(draft) {
      const fields = {
        title: String(draft.title || '').trim(),
        subject: String(draft.subject || '').trim(),
        dueAt: String(draft.dueAt || '').trim(),
        priority: String(draft.priority || 'medium').trim() || 'medium',
        note: String(draft.note || '').trim()
      };
      if (!fields.title) throw new Error('标题不能为空');
      if (fields.title.length > 80) throw new Error('标题不能超过 80 个字符');
      if (!fields.subject) throw new Error('科目不能为空');
      if (fields.subject.length > 40) throw new Error('科目不能超过 40 个字符');
      if (!['high', 'medium', 'low'].includes(fields.priority)) throw new Error('优先级无效');
      if (fields.dueAt && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00$/.test(fields.dueAt)) {
        throw new Error('截止时间必须为空，或使用 YYYY-MM-DDTHH:mm:00');
      }
      if (fields.dueAt && Number.isNaN(new Date(fields.dueAt).getTime())) {
        throw new Error('截止时间不是有效日期');
      }
      return fields;
    },
    aiPatchFromDraft(action, existing) {
      const fields = this.normalizeAiDraftFields(action.draft || {});
      const patch = {};
      ['title', 'subject', 'dueAt', 'priority', 'note'].forEach(field => {
        if (String(fields[field] || '') !== String(existing[field] || '')) {
          patch[field] = fields[field];
        }
      });
      return patch;
    },
    markAiAction(action, status, message = '') {
      this.aiActionResults = this.aiActionResults.map(result => (
        result.actionId === action.id ? { ...result, status, message } : result
      ));
    },
    aiApprovalCounts() {
      return this.aiActionResults.reduce((summary, result) => {
        summary[result.status] = (summary[result.status] || 0) + 1;
        return summary;
      }, {});
    },
    aiApprovalProgressText() {
      const counts = this.aiApprovalCounts();
      return `已执行 ${counts.executed || 0} · 已取消 ${counts.canceled || 0} · 待处理 ${counts.pending || 0}`;
    },
    appendAiActionSummary() {
      const counts = this.aiApprovalCounts();
      const parts = [
        `已执行 ${counts.executed || 0} 条`,
        `已取消 ${counts.canceled || 0} 条`,
        `未处理 ${counts.pending || 0} 条`
      ];
      const details = this.aiPendingActions.map((action, index) => {
        const result = this.aiActionResult(action);
        const status = result ? this.aiActionStatusLabel(action) : '待审批';
        const message = result && result.message ? `，${result.message}` : '';
        return `${index + 1}. ${action.summary}：${status}${message}`;
      });
      this.aiChatMessages.push({
        role: 'assistant',
        kind: 'approval-result',
        content: `审批结果：${parts.join('，')}。\n${details.join('\n')}`
      });
      this.scrollAiChatToBottom();
      this.aiPendingActions = [];
      this.aiActionResults = [];
      this.aiCurrentActionIndex = 0;
      this.aiExecutingActionId = '';
    },
    canCloseAiApproval() {
      if (this.aiExecutingActionId) return false;
      return this.aiActionResults.every(result => result.status !== 'pending');
    },
    closeAiApproval() {
      if (!this.canCloseAiApproval()) return;
      this.aiApprovalVisible = false;
      this.appendAiActionSummary();
    },
    aiTaskPayloadFromFields(fields) {
      return {
        id: this.createTaskId(),
        createdAt: new Date().toISOString(),
        title: String(fields.title || '').trim(),
        subject: String(fields.subject || '').trim(),
        dueAt: String(fields.dueAt || '').trim(),
        pool: 'todo',
        priority: fields.priority || 'medium',
        note: String(fields.note || '').trim(),
        completed: false
      };
    },
    async approveAiAction(action) {
      if (!action || this.aiExecutingActionId) return;
      if (this.aiActionStatus(action) === 'executed') return;
      this.aiExecutingActionId = action.id;
      try {
        if (action.type === 'create_task') {
          const task = this.aiTaskPayloadFromFields(this.normalizeAiDraftFields(action.draft || {}));
          const savedTask = await this.createTaskOnServer(task);
          this.tasks = [...this.tasks, savedTask || task];
          this.markAiAction(action, 'executed', '任务已创建');
          ElementPlus.ElMessage.success('AI 指令已执行：任务已创建。');
        } else if (action.type === 'update_task') {
          const existing = this.tasks.find(task => task.id === action.targetTaskId);
          if (!existing) throw new Error('目标任务不存在或已变化');
          const patch = this.aiPatchFromDraft(action, existing);
          if (!Object.keys(patch).length) throw new Error('没有实际变更');
          const nextTask = { ...existing, ...patch, updatedAt: new Date().toISOString() };
          const savedTask = await this.updateTaskOnServer(action.targetTaskId, nextTask);
          this.tasks = this.tasks.map(task => task.id === action.targetTaskId ? (savedTask || nextTask) : task);
          await this.loadScheduleItems();
          this.markAiAction(action, 'executed', '任务已更新');
          ElementPlus.ElMessage.success('AI 指令已执行：任务已更新。');
        } else {
          throw new Error('不支持的 AI 指令');
        }
      } catch (error) {
        console.error('AI 指令执行失败：', error);
        this.markAiAction(action, 'pending', `执行失败：${error.message}`);
        ElementPlus.ElMessage.error(`AI 指令执行失败：${error.message}`);
      } finally {
        this.aiExecutingActionId = '';
      }
    },
    cancelAiAction(action) {
      if (!action || this.aiExecutingActionId) return;
      this.markAiAction(action, 'canceled', '用户取消');
    },
    defaultSubjectTemplate() {
      return JSON.parse(JSON.stringify(DEFAULT_SUBJECT_TEMPLATE));
    },
    normalizeSubjectTemplate(subjects) {
      const source = Array.isArray(subjects) ? subjects : this.defaultSubjectTemplate();
      const byName = new Map();
      source.forEach(item => {
        if (!item || typeof item !== 'object') return;
        const name = String(item.name || '').trim();
        if (!name || name.length > 40) return;
        byName.set(name.toLocaleLowerCase(), { ...item, name });
      });
      const normalized = this.defaultSubjectTemplate().map(item => {
        const raw = byName.get(item.name.toLocaleLowerCase());
        return { name: item.name, preset: true, enabled: raw ? !!raw.enabled : true };
      });
      const seen = new Set(normalized.map(item => item.name.toLocaleLowerCase()));
      source.forEach(item => {
        if (!item || typeof item !== 'object') return;
        const name = String(item.name || '').trim();
        const key = name.toLocaleLowerCase();
        if (!name || name.length > 40 || seen.has(key)) return;
        normalized.push({ name, preset: false, enabled: item.enabled !== false });
        seen.add(key);
      });
      return normalized;
    },
    resetSubjectTemplateState() {
      this.subjectTemplate = this.defaultSubjectTemplate();
      this.subjectTemplateDraft = [];
      this.subjectTemplateDialogVisible = false;
      this.newSubjectName = '';
      this.lastSubjectBeforeTemplateEdit = '';
    },
    async loadSubjectTemplate() {
      if (!this.currentUser) {
        this.resetSubjectTemplateState();
        return;
      }
      try {
        const payload = await this.apiJson(SUBJECT_TEMPLATE_API, { cache: 'no-store' });
        this.subjectTemplate = this.normalizeSubjectTemplate(payload.subjects);
      } catch (error) {
        this.subjectTemplate = this.defaultSubjectTemplate();
        ElementPlus.ElMessage.error(`科目模板读取失败：${error.message}`);
      }
    },
    rememberSubjectBeforeTemplateEdit() {
      this.lastSubjectBeforeTemplateEdit = this.form.subject;
    },
    handleSubjectSelectChange(value) {
      if (value !== SUBJECT_TEMPLATE_EDIT_VALUE) {
        this.lastSubjectBeforeTemplateEdit = value;
        return;
      }
      this.form.subject = this.lastSubjectBeforeTemplateEdit || '';
      this.openSubjectTemplateDialog();
    },
    openSubjectTemplateDialog() {
      this.subjectTemplateDraft = this.normalizeSubjectTemplate(this.subjectTemplate);
      this.newSubjectName = '';
      this.subjectTemplateDialogVisible = true;
    },
    addSubjectTemplateItem() {
      const name = this.newSubjectName.trim();
      if (!name) {
        ElementPlus.ElMessage.warning('科目名称不能为空。');
        return;
      }
      if (name.length > 40) {
        ElementPlus.ElMessage.warning('科目名称不能超过 40 个字符。');
        return;
      }
      const exists = this.subjectTemplateDraft.some(item => item.name.toLocaleLowerCase() === name.toLocaleLowerCase());
      if (exists) {
        ElementPlus.ElMessage.warning('这个科目已经存在。');
        return;
      }
      this.subjectTemplateDraft.push({ name, preset: false, enabled: true });
      this.newSubjectName = '';
    },
    removeSubjectTemplateItem(index) {
      const item = this.subjectTemplateDraft[index];
      if (!item || item.preset) return;
      this.subjectTemplateDraft.splice(index, 1);
    },
    async saveSubjectTemplate() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录后再保存科目模板。');
        return;
      }
      const normalized = this.normalizeSubjectTemplate(this.subjectTemplateDraft);
      try {
        const payload = await this.apiJson(SUBJECT_TEMPLATE_API, {
          method: 'PUT',
          body: JSON.stringify({ subjects: normalized })
        });
        this.subjectTemplate = this.normalizeSubjectTemplate(payload.subjects);
        this.subjectTemplateDialogVisible = false;
        ElementPlus.ElMessage.success('科目模板已保存。');
      } catch (error) {
        ElementPlus.ElMessage.error(`科目模板保存失败：${error.message}`);
      }
    },
    async openAdminMode(section = 'users') {
      if (!this.isAdmin) {
        ElementPlus.ElMessage.warning('只有管理员可以进入后台。');
        return;
      }
      this.accountMenuOpen = false;
      this.adminMode = true;
      this.adminSection = section;
      await this.loadAdminUsers();
      if (!this.adminSelectedUserId && this.adminUsers.length) {
        this.adminSelectedUserId = String(this.adminUsers[0].id);
      }
      if (this.adminSection === 'logs') await this.loadAdminLogs(1);
      if (this.adminSection === 'timeline') await this.loadAdminTimeline();
      if (this.adminSection === 'feedback') await this.loadAdminFeedback(1);
      if (this.adminSection === 'traffic') await this.loadAdminTraffic();
      if (this.adminSection === 'aiUsage') await this.loadAdminAiUsage();
      await this.recordVisit('admin');
    },
    async exitAdminMode() {
      this.adminMode = false;
      this.adminTimelineLoadedUserId = '';
      await this.loadScheduleConfig();
      await this.loadTasks();
      await this.loadHabits();
      await this.loadScheduleItems();
      this.$nextTick(() => this.scrollToDate(this.currentViewDateKey || new Date(), this.activePage, 'instant'));
    },
    async switchAdminSection(section) {
      this.adminSection = section;
      if (section === 'users') await this.loadAdminUsers();
      if (section === 'logs') await this.loadAdminLogs(1);
      if (section === 'timeline') await this.loadAdminTimeline();
      if (section === 'feedback') await this.loadAdminFeedback(1);
      if (section === 'traffic') await this.loadAdminTraffic();
      if (section === 'aiUsage') await this.loadAdminAiUsage();
    },
    async recordVisit(page) {
      try {
        await this.apiJson(VISITS_API, {
          method: 'POST',
          body: JSON.stringify({
            page,
            path: `${window.location.pathname}${window.location.search}#${page}`
          })
        });
      } catch (error) {
        console.warn('访问记录上报失败：', error);
      }
    },
    async loadAdminUsers() {
      if (!this.isAdmin) return;
      this.adminLoading = true;
      try {
        const payload = await this.apiJson(`${ADMIN_API}/users`, { cache: 'no-store' });
        this.adminUsers = Array.isArray(payload.users) ? payload.users : [];
        const maxPage = Math.max(1, Math.ceil(this.adminUsers.length / this.adminUsersPageSize));
        this.adminUsersPage = Math.min(this.adminUsersPage, maxPage);
      } catch (error) {
        ElementPlus.ElMessage.error(`后台用户列表读取失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    startAdminUserNameEdit(user) {
      if (!this.isAdmin || !user) return;
      this.adminEditingUserId = String(user.id);
      this.adminEditingName = user.name || '';
    },
    cancelAdminUserNameEdit() {
      this.adminEditingUserId = '';
      this.adminEditingName = '';
    },
    async saveAdminUserName(user) {
      if (!this.isAdmin || !user) return;
      const name = this.adminEditingName.trim();
      if (!name) {
        ElementPlus.ElMessage.warning('姓名不能为空。');
        return;
      }
      if (name === user.name) {
        this.cancelAdminUserNameEdit();
        return;
      }
      this.adminLoading = true;
      try {
        const payload = await this.apiJson(`${ADMIN_API}/users/${encodeURIComponent(user.id)}`, {
          method: 'PUT',
          body: JSON.stringify({ name })
        });
        const updatedUser = payload.user || { ...user, name };
        this.adminUsers = this.adminUsers.map(item => (
          String(item.id) === String(user.id) ? { ...item, name: updatedUser.name || name } : item
        ));
        if (this.currentUser && Number(this.currentUser.id) === Number(user.id)) {
          this.currentUser = { ...this.currentUser, name: updatedUser.name || name };
        }
        this.cancelAdminUserNameEdit();
        ElementPlus.ElMessage.success('姓名已更新。');
      } catch (error) {
        ElementPlus.ElMessage.error(`姓名更新失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    deleteAdminUser(user) {
      if (!this.isAdmin || !user) return;
      if (this.currentUser && Number(user.id) === Number(this.currentUser.id)) {
        ElementPlus.ElMessage.warning('不能删除当前登录的管理员账号。');
        return;
      }
      ElementPlus.ElMessageBox.confirm(
        `确定删除用户「${user.name}（${user.nickname}）」？该用户的任务、每日安排、时间格子配置和登录会话都会被删除。`,
        '删除用户',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        this.adminLoading = true;
        try {
          await this.apiJson(`${ADMIN_API}/users/${encodeURIComponent(user.id)}`, { method: 'DELETE' });
          if (String(this.adminSelectedUserId) === String(user.id)) {
            this.adminSelectedUserId = '';
            this.adminLogs = [];
            this.adminLogsTotal = 0;
            this.adminTimelineLoadedUserId = '';
          }
          await this.loadAdminUsers();
          if (!this.adminSelectedUserId && this.adminUsers.length) {
            this.adminSelectedUserId = String(this.adminUsers[0].id);
          }
          ElementPlus.ElMessage.success('用户已删除。');
        } catch (error) {
          ElementPlus.ElMessage.error(`删除用户失败：${error.message}`);
        } finally {
          this.adminLoading = false;
        }
      }).catch(() => {});
    },
    async handleAdminUserChange() {
      if (this.adminSection === 'logs') await this.loadAdminLogs(1);
      if (this.adminSection === 'timeline') await this.loadAdminTimeline();
    },
    async loadAdminLogs(page = this.adminLogsPage) {
      if (!this.isAdmin || !this.adminSelectedUserId) {
        this.adminLogs = [];
        this.adminLogsTotal = 0;
        return;
      }
      this.adminLoading = true;
      try {
        const url = `${ADMIN_API}/users/${this.adminSelectedUserId}/logs?page=${page}&pageSize=${this.adminLogsPageSize}`;
        const payload = await this.apiJson(url, { cache: 'no-store' });
        this.adminLogs = Array.isArray(payload.logs) ? payload.logs : [];
        this.adminLogsTotal = Number(payload.total || 0);
        this.adminLogsPage = Number(payload.page || page);
      } catch (error) {
        ElementPlus.ElMessage.error(`日志读取失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    async loadAdminFeedback(page = this.adminFeedbackPage) {
      if (!this.isAdmin) {
        this.adminFeedback = [];
        this.adminFeedbackTotal = 0;
        return;
      }
      this.adminLoading = true;
      try {
        const url = `${ADMIN_API}/feedback?page=${page}&pageSize=${this.adminFeedbackPageSize}`;
        const payload = await this.apiJson(url, { cache: 'no-store' });
        this.adminFeedback = Array.isArray(payload.feedback) ? payload.feedback : [];
        this.adminFeedbackTotal = Number(payload.total || 0);
        this.adminFeedbackPage = Number(payload.page || page);
        this.feedbackLimitPerUser = Number(payload.feedbackLimitPerUser || this.feedbackLimitPerUser);
        this.adminFeedbackLimitDraft = this.feedbackLimitPerUser;
      } catch (error) {
        ElementPlus.ElMessage.error(`反馈读取失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    async loadAdminTraffic(page = this.adminTrafficRecentPage) {
      if (!this.isAdmin) return;
      const nextPage = Number(page);
      const safePage = Number.isFinite(nextPage) && nextPage > 0 ? Math.floor(nextPage) : this.adminTrafficRecentPage;
      this.adminLoading = true;
      try {
        const url = `${ADMIN_API}/traffic/summary?view=${encodeURIComponent(this.adminTrafficView)}&page=${safePage}&pageSize=${this.adminTrafficRecentPageSize}`;
        const payload = await this.apiJson(url, { cache: 'no-store' });
        this.adminTraffic = {
          seriesUnit: payload.seriesUnit || 'day',
          totalVisits: Number(payload.totalVisits || 0),
          todayVisits: Number(payload.todayVisits || 0),
          uniqueIps: Number(payload.uniqueIps || 0),
          todayUniqueIps: Number(payload.todayUniqueIps || 0),
          trendSeries: Array.isArray(payload.trendSeries) ? payload.trendSeries : [],
          dailySeries: Array.isArray(payload.dailySeries) ? payload.dailySeries : [],
          topIps: Array.isArray(payload.topIps) ? payload.topIps : [],
          recentVisits: Array.isArray(payload.recentVisits) ? payload.recentVisits : []
        };
        this.adminTrafficRecentTotal = Number(payload.recentTotal || 0);
        this.adminTrafficRecentPage = Number(payload.page || safePage);
      } catch (error) {
        ElementPlus.ElMessage.error(`流量统计读取失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    async switchAdminTrafficView(view) {
      if (view === this.adminTrafficView) return;
      this.adminTrafficView = view;
      this.adminTrafficHoverPoint = null;
      await this.loadAdminTraffic(this.adminTrafficRecentPage);
    },
    showTrafficPoint(point) {
      this.adminTrafficHoverPoint = point;
    },
    hideTrafficPoint() {
      this.adminTrafficHoverPoint = null;
    },
    normalizeAiLimitDraft(limit) {
      const windowHours = Number(limit && limit.windowHours);
      const inputTokenLimit = Number(limit && limit.inputTokenLimit);
      const outputTokenLimit = Number(limit && limit.outputTokenLimit);
      if (!Number.isInteger(windowHours) || windowHours < 1 || windowHours > 8760) {
        throw new Error('窗口小时数必须是 1 到 8760 之间的整数。');
      }
      if (!Number.isInteger(inputTokenLimit) || inputTokenLimit < 1 || inputTokenLimit > 10000000000) {
        throw new Error('输入 token 上限必须是 1 到 10000000000 之间的整数。');
      }
      if (!Number.isInteger(outputTokenLimit) || outputTokenLimit < 1 || outputTokenLimit > 10000000000) {
        throw new Error('输出 token 上限必须是 1 到 10000000000 之间的整数。');
      }
      return { windowHours, inputTokenLimit, outputTokenLimit };
    },
    aiLimitDraftFromLimit(limit) {
      return {
        windowHours: Number(limit && limit.windowHours ? limit.windowHours : 24),
        inputTokenLimit: Number(limit && limit.inputTokenLimit ? limit.inputTokenLimit : 200000),
        outputTokenLimit: Number(limit && limit.outputTokenLimit ? limit.outputTokenLimit : 50000)
      };
    },
    async loadAdminAiUsage(page = this.adminAiUsagePage) {
      if (!this.isAdmin) return;
      const nextPage = Number(page);
      const safePage = Number.isFinite(nextPage) && nextPage > 0 ? Math.floor(nextPage) : this.adminAiUsagePage;
      this.adminLoading = true;
      try {
        const url = `${ADMIN_API}/ai-usage/summary?view=${encodeURIComponent(this.adminAiUsageView)}&page=${safePage}&pageSize=${this.adminAiUsagePageSize}`;
        const payload = await this.apiJson(url, { cache: 'no-store' });
        const globalLimit = this.aiLimitDraftFromLimit(payload.globalLimit);
        const users = Array.isArray(payload.users) ? payload.users : [];
        this.adminAiUsage = {
          seriesUnit: payload.seriesUnit || 'day',
          globalLimit,
          totalPromptTokens: Number(payload.totalPromptTokens || 0),
          totalCompletionTokens: Number(payload.totalCompletionTokens || 0),
          totalCalls: Number(payload.totalCalls || 0),
          todayPromptTokens: Number(payload.todayPromptTokens || 0),
          todayCompletionTokens: Number(payload.todayCompletionTokens || 0),
          todayCalls: Number(payload.todayCalls || 0),
          trendSeries: Array.isArray(payload.trendSeries) ? payload.trendSeries : [],
          users
        };
        this.adminAiGlobalLimitDraft = this.aiLimitDraftFromLimit(globalLimit);
        this.adminAiUserLimitDrafts = users.reduce((drafts, row) => {
          const id = row && row.user ? String(row.user.id) : '';
          if (!id) return drafts;
          drafts[id] = this.aiLimitDraftFromLimit(row.effectiveLimit || globalLimit);
          return drafts;
        }, {});
        this.adminAiUsageUsersTotal = Number(payload.usersTotal || 0);
        this.adminAiUsagePage = Number(payload.page || safePage);
        this.adminAiUsageHoverPoint = null;
      } catch (error) {
        ElementPlus.ElMessage.error(`Token 使用情况读取失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    async switchAdminAiUsageView(view) {
      if (view === this.adminAiUsageView) return;
      this.adminAiUsageView = view;
      this.adminAiUsageHoverPoint = null;
      await this.loadAdminAiUsage(this.adminAiUsagePage);
    },
    showAiUsagePoint(point) {
      this.adminAiUsageHoverPoint = point;
    },
    hideAiUsagePoint() {
      this.adminAiUsageHoverPoint = null;
    },
    formatTokenCount(value) {
      const number = Number(value || 0);
      return new Intl.NumberFormat('zh-CN').format(Number.isFinite(number) ? number : 0);
    },
    aiLimitSourceLabel(row) {
      return row && row.hasOverride ? '个人覆盖' : '全局';
    },
    aiLimitSourceType(row) {
      return row && row.hasOverride ? 'warning' : 'info';
    },
    aiLimitText(limit) {
      const safe = this.aiLimitDraftFromLimit(limit);
      return `${safe.windowHours} 小时 · 输入 ${this.formatTokenCount(safe.inputTokenLimit)} · 输出 ${this.formatTokenCount(safe.outputTokenLimit)}`;
    },
    aiWindowUsageText(usage) {
      const safe = usage || {};
      return `输入 ${this.formatTokenCount(safe.promptTokens)} / 输出 ${this.formatTokenCount(safe.completionTokens)}`;
    },
    async saveAdminAiGlobalLimit() {
      if (!this.isAdmin) return;
      let limit;
      try {
        limit = this.normalizeAiLimitDraft(this.adminAiGlobalLimitDraft);
      } catch (error) {
        ElementPlus.ElMessage.warning(error.message);
        return;
      }
      this.adminLoading = true;
      try {
        await this.apiJson(`${ADMIN_API}/ai-usage/global-limit`, {
          method: 'PUT',
          body: JSON.stringify(limit)
        });
        ElementPlus.ElMessage.success('全局 Token 限制已保存。');
        await this.loadAdminAiUsage(this.adminAiUsagePage);
      } catch (error) {
        ElementPlus.ElMessage.error(`全局 Token 限制保存失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    async saveAdminAiUserLimit(row) {
      if (!this.isAdmin || !row || !row.user) return;
      const userId = String(row.user.id);
      let limit;
      try {
        limit = this.normalizeAiLimitDraft(this.adminAiUserLimitDrafts[userId]);
      } catch (error) {
        ElementPlus.ElMessage.warning(error.message);
        return;
      }
      this.adminLoading = true;
      try {
        await this.apiJson(`${ADMIN_API}/users/${encodeURIComponent(userId)}/ai-token-limit`, {
          method: 'PUT',
          body: JSON.stringify(limit)
        });
        ElementPlus.ElMessage.success('用户 Token 限制已保存。');
        await this.loadAdminAiUsage(this.adminAiUsagePage);
      } catch (error) {
        ElementPlus.ElMessage.error(`用户 Token 限制保存失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    async clearAdminAiUserLimit(row) {
      if (!this.isAdmin || !row || !row.user) return;
      const userId = String(row.user.id);
      this.adminLoading = true;
      try {
        await this.apiJson(`${ADMIN_API}/users/${encodeURIComponent(userId)}/ai-token-limit`, { method: 'DELETE' });
        ElementPlus.ElMessage.success('该用户已恢复全局限制。');
        await this.loadAdminAiUsage(this.adminAiUsagePage);
      } catch (error) {
        ElementPlus.ElMessage.error(`恢复全局限制失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    async clearAllAdminAiUserLimits() {
      if (!this.isAdmin) return;
      ElementPlus.ElMessageBox.confirm(
        '确定清除所有用户个人 Token 限制，让所有用户重新使用全局设置？',
        '统一全局限制',
        {
          confirmButtonText: '统一全局',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        this.adminLoading = true;
        try {
          await this.apiJson(`${ADMIN_API}/ai-usage/clear-user-limits`, { method: 'POST' });
          ElementPlus.ElMessage.success('所有用户已恢复全局限制。');
          await this.loadAdminAiUsage(this.adminAiUsagePage);
        } catch (error) {
          ElementPlus.ElMessage.error(`统一全局失败：${error.message}`);
        } finally {
          this.adminLoading = false;
        }
      }).catch(() => {});
    },
    async saveAdminFeedbackLimit() {
      if (!this.isAdmin) return;
      const feedbackLimitPerUser = Number(this.adminFeedbackLimitDraft);
      if (!Number.isInteger(feedbackLimitPerUser) || feedbackLimitPerUser < 1 || feedbackLimitPerUser > 1000) {
        ElementPlus.ElMessage.warning('未回复反馈上限必须是 1 到 1000 之间的整数。');
        return;
      }
      this.adminLoading = true;
      try {
        const payload = await this.apiJson(`${ADMIN_API}/feedback-settings`, {
          method: 'PUT',
          body: JSON.stringify({ feedbackLimitPerUser })
        });
        this.feedbackLimitPerUser = Number(payload.feedbackLimitPerUser || feedbackLimitPerUser);
        this.adminFeedbackLimitDraft = this.feedbackLimitPerUser;
        ElementPlus.ElMessage.success('未回复反馈上限已更新。');
      } catch (error) {
        ElementPlus.ElMessage.error(`未回复反馈上限保存失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    openAdminFeedbackReply(row) {
      if (!this.isAdmin || !row) return;
      this.adminFeedbackActive = row;
      this.adminFeedbackReply = row.adminReply || '';
      this.adminFeedbackReplyVisible = true;
    },
    async saveAdminFeedbackReply() {
      if (!this.isAdmin || !this.adminFeedbackActive) return;
      const reply = this.adminFeedbackReply.trim();
      if (!reply) {
        ElementPlus.ElMessage.warning('回复内容不能为空。');
        return;
      }
      this.adminLoading = true;
      try {
        await this.apiJson(`${ADMIN_API}/feedback/${encodeURIComponent(this.adminFeedbackActive.id)}/reply`, {
          method: 'PUT',
          body: JSON.stringify({ reply })
        });
        this.adminFeedbackReplyVisible = false;
        this.adminFeedbackActive = null;
        this.adminFeedbackReply = '';
        await this.loadAdminFeedback(this.adminFeedbackPage);
        ElementPlus.ElMessage.success('反馈回复已保存。');
      } catch (error) {
        ElementPlus.ElMessage.error(`回复保存失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    deleteAdminFeedback(row) {
      if (!this.isAdmin || !row) return;
      ElementPlus.ElMessageBox.confirm(
        `确定删除这条反馈？用户「${row.user ? `${row.user.name}（${row.user.nickname}）` : row.userId}」提交的内容会被删除。`,
        '删除反馈',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        this.adminLoading = true;
        try {
          await this.apiJson(`${ADMIN_API}/feedback/${encodeURIComponent(row.id)}`, { method: 'DELETE' });
          const nextPage = this.adminFeedback.length <= 1 && this.adminFeedbackPage > 1
            ? this.adminFeedbackPage - 1
            : this.adminFeedbackPage;
          await this.loadAdminFeedback(nextPage);
          ElementPlus.ElMessage.success('反馈已删除。');
        } catch (error) {
          ElementPlus.ElMessage.error(`删除反馈失败：${error.message}`);
        } finally {
          this.adminLoading = false;
        }
      }).catch(() => {});
    },
    async loadAdminTimeline() {
      if (!this.isAdmin || !this.adminSelectedUserId) {
        this.tasks = [];
        this.scheduleItems = [];
        this.habits = [];
        this.habitSyncConflicts = [];
        return;
      }
      this.adminLoading = true;
      try {
        const userId = this.adminSelectedUserId;
        const range = this.scheduleSyncRange();
        const [taskPayload, itemPayload, habitPayload, configPayload] = await Promise.all([
          this.apiJson(`${ADMIN_API}/users/${userId}/tasks`, { cache: 'no-store' }),
          this.apiJson(`${ADMIN_API}/users/${userId}/schedule-items?from=${encodeURIComponent(range.from)}&to=${encodeURIComponent(range.to)}`, { cache: 'no-store' }),
          this.apiJson(`${ADMIN_API}/users/${userId}/habits`, { cache: 'no-store' }),
          this.apiJson(`${ADMIN_API}/users/${userId}/schedule-config`, { cache: 'no-store' })
        ]);
        this.tasks = Array.isArray(taskPayload.tasks) ? taskPayload.tasks.map(task => this.normalizeTaskPool(task)) : [];
        this.scheduleItems = Array.isArray(itemPayload.items) ? itemPayload.items : [];
        this.habits = Array.isArray(habitPayload.habits) ? habitPayload.habits : [];
        this.habitSyncConflicts = Array.isArray(itemPayload.habitSyncConflicts) ? itemPayload.habitSyncConflicts : [];
        this.defaultWeekSlots = this.cloneSlots(configPayload.defaultWeekSlots || DEFAULT_WEEK_SLOTS);
        this.scheduleTemplateVersions = Array.isArray(configPayload.templateVersions) ? configPayload.templateVersions : [];
        this.scheduleDayOverrides = configPayload.dayOverrides && typeof configPayload.dayOverrides === 'object' ? configPayload.dayOverrides : {};
        this.adminTimelineLoadedUserId = String(userId);
        this.$nextTick(() => this.scrollToDate(this.currentViewDateKey || new Date(), this.activePage, 'instant'));
      } catch (error) {
        ElementPlus.ElMessage.error(`用户时间表读取失败：${error.message}`);
      } finally {
        this.adminLoading = false;
      }
    },
    adminActionLabel(action) {
      const labels = {
        'auth.register': '注册',
        'auth.login': '登录',
        'task.create': '新增任务',
        'task.update': '更新任务',
        'task.complete': '完成任务',
        'task.reopen': '取消完成任务',
        'task.delete': '删除任务',
        'schedule_item.create': '新增每日安排',
        'schedule_item.update': '更新每日安排',
        'schedule_item.complete': '完成每日安排',
        'schedule_item.reopen': '取消完成每日安排',
        'schedule_item.delete': '删除每日安排',
        'schedule_config.template_update': '更新一周模板',
        'schedule_config.day_update': '更新单日时间格子',
        'schedule_config.day_reset': '重置单日时间格子',
        'schedule_config.reset': '重置全部时间格子',
        'admin.user.delete': '删除用户',
        'admin.user.update': '更新用户',
        'user.nickname.update': '修改昵称',
        'user.password.update': '修改密码',
        'feedback.create': '提交反馈',
        'admin.feedback.reply': '回复反馈',
        'admin.feedback.delete': '删除反馈',
        'admin.feedback.limit_update': '修改未回复反馈上限',
        'feedback.delete': '删除反馈',
        'subject_template.update': '更新科目模板',
        'admin.ai_token.global_limit_update': '修改 AI 全局 Token 限制',
        'admin.ai_token.user_limit_update': '修改用户 AI Token 限制',
        'admin.ai_token.user_limit_clear': '清除用户 AI Token 覆盖',
        'admin.ai_token.user_limits_clear_all': '清除全部 AI Token 覆盖'
      };
      return labels[action] || action;
    },
    visitPageLabel(page) {
      const labels = {
        home: '主页',
        admin: '管理员后台'
      };
      return labels[page] || page || '未知';
    },
    visitUserLabel(visit) {
      if (!visit || !visit.user) return '—';
      return `${visit.user.name}（${visit.user.nickname}）`;
    },
    formatTrafficDate(dateKey) {
      if (!dateKey) return '';
      if (String(dateKey).includes('T')) {
        const date = new Date(dateKey);
        if (!Number.isNaN(date.getTime())) return `${this.pad(date.getHours())}:00`;
      }
      const [, month, day] = String(dateKey).split('-');
      return month && day ? `${Number(month)}/${Number(day)}` : String(dateKey);
    },
    formatTrafficTooltipTime(dateKey) {
      if (!dateKey) return '未知时间';
      if (String(dateKey).includes('T')) {
        const date = new Date(dateKey);
        if (!Number.isNaN(date.getTime())) {
          return `${date.getFullYear()}-${this.pad(date.getMonth() + 1)}-${this.pad(date.getDate())} ${this.pad(date.getHours())}:00`;
        }
      }
      return String(dateKey);
    },
    adminLogDetail(log) {
      const detail = log && log.detail ? log.detail : {};
      return Object.entries(detail)
        .filter(([, value]) => value !== null && value !== undefined && value !== '')
        .map(([key, value]) => `${key}: ${value}`)
        .join('；');
    },
    async loadCurrentUser() {
      if (!this.authToken) return;
      try {
        const payload = await this.apiJson(`${AUTH_API}/me`, { cache: 'no-store' });
        this.currentUser = payload.user;
      } catch (error) {
        this.authToken = '';
        this.currentUser = null;
        localStorage.removeItem(AUTH_TOKEN_KEY);
      }
    },
    async login() {
      try {
        const payload = await this.apiJson(`${AUTH_API}/login`, {
          method: 'POST',
          body: JSON.stringify(this.loginForm)
        });
        this.authToken = payload.token;
        this.currentUser = payload.user;
        this.accountMenuOpen = false;
        localStorage.setItem(AUTH_TOKEN_KEY, payload.token);
        await this.loadSubjectTemplate();
        await this.loadScheduleConfig();
        await this.loadTasks();
        await this.loadHabits();
        await this.loadScheduleItems();
        ElementPlus.ElMessage.success('登录成功。');
      } catch (error) {
        ElementPlus.ElMessage.error(`登录失败：${error.message}`);
      }
    },
    async register() {
      try {
        const payload = await this.apiJson(`${AUTH_API}/register`, {
          method: 'POST',
          body: JSON.stringify(this.registerForm)
        });
        this.authToken = payload.token;
        this.currentUser = payload.user;
        this.accountMenuOpen = false;
        localStorage.setItem(AUTH_TOKEN_KEY, payload.token);
        await this.loadSubjectTemplate();
        await this.loadScheduleConfig();
        await this.loadTasks();
        await this.loadHabits();
        await this.loadScheduleItems();
        ElementPlus.ElMessage.success('注册成功，已自动登录。');
      } catch (error) {
        ElementPlus.ElMessage.error(`注册失败：${error.message}`);
      }
    },
    openNicknameDialog() {
      if (!this.currentUser) return;
      this.accountMenuOpen = false;
      this.nicknameForm.nickname = this.currentUser.nickname || '';
      this.nicknameDialogVisible = true;
    },
    openPasswordDialog() {
      if (!this.currentUser) return;
      this.accountMenuOpen = false;
      this.passwordForm = { currentPassword: '', newPassword: '', confirmPassword: '' };
      this.passwordDialogVisible = true;
    },
    async saveNickname() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录后再修改昵称。');
        return;
      }
      const nickname = this.nicknameForm.nickname.trim();
      if (!nickname) {
        ElementPlus.ElMessage.warning('昵称不能为空。');
        return;
      }
      if (nickname === this.currentUser.nickname) {
        this.nicknameDialogVisible = false;
        return;
      }
      try {
        const payload = await this.apiJson(`${AUTH_API}/nickname`, {
          method: 'PUT',
          body: JSON.stringify({ nickname })
        });
        this.currentUser = payload.user;
        this.loginForm.nickname = payload.user.nickname;
        this.nicknameDialogVisible = false;
        ElementPlus.ElMessage.success('昵称已更新。');
      } catch (error) {
        ElementPlus.ElMessage.error(`昵称更新失败：${error.message}`);
      }
    },
    async savePassword() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录后再修改密码。');
        return;
      }
      const currentPassword = this.passwordForm.currentPassword;
      const newPassword = this.passwordForm.newPassword;
      if (!currentPassword || !newPassword || !this.passwordForm.confirmPassword) {
        ElementPlus.ElMessage.warning('请完整填写密码信息。');
        return;
      }
      if (newPassword.length < 6) {
        ElementPlus.ElMessage.warning('新密码至少需要 6 位。');
        return;
      }
      if (newPassword !== this.passwordForm.confirmPassword) {
        ElementPlus.ElMessage.warning('两次输入的新密码不一致。');
        return;
      }
      try {
        await this.apiJson(`${AUTH_API}/password`, {
          method: 'PUT',
          body: JSON.stringify({ currentPassword, newPassword })
        });
        this.passwordDialogVisible = false;
        this.passwordForm = { currentPassword: '', newPassword: '', confirmPassword: '' };
        ElementPlus.ElMessage.success('密码已更新。');
      } catch (error) {
        ElementPlus.ElMessage.error(`密码更新失败：${error.message}`);
      }
    },
    openAvatarDialog() {
      if (!this.currentUser) return;
      this.accountMenuOpen = false;
      this.resetAvatarDraft();
      this.avatarDialogVisible = true;
    },
    resetAvatarDraft() {
      if (this.avatarSourceUrl) URL.revokeObjectURL(this.avatarSourceUrl);
      this.avatarSourceUrl = '';
      this.avatarSourceName = '';
      this.avatarSourceType = '';
      this.avatarImage = null;
      this.avatarPreviewUrl = '';
      this.avatarCrop = {
        x: 0,
        y: 0,
        scale: 1,
        minScale: 1,
        maxScale: 4,
        dragging: false,
        pointerId: null,
        startX: 0,
        startY: 0,
        originX: 0,
        originY: 0
      };
      this.avatarColorDraft = this.avatarColor;
      if (this.$refs.avatarFileInput) this.$refs.avatarFileInput.value = '';
    },
    chooseAvatarFile() {
      if (this.$refs.avatarFileInput) this.$refs.avatarFileInput.click();
    },
    handleAvatarFileChange(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      if (!AVATAR_ALLOWED_TYPES.includes(file.type)) {
        ElementPlus.ElMessage.warning('请选择 PNG、JPEG 或 WebP 图片。');
        event.target.value = '';
        return;
      }
      if (file.size > AVATAR_SOURCE_MAX_BYTES) {
        ElementPlus.ElMessage.warning('原图不能超过 8MB。');
        event.target.value = '';
        return;
      }
      const colorDraft = this.avatarDraftColor;
      this.resetAvatarDraft();
      this.avatarColorDraft = colorDraft;
      this.avatarSourceName = file.name || 'avatar.png';
      this.avatarSourceType = file.type;
      const objectUrl = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => {
        this.avatarSourceUrl = objectUrl;
        this.avatarImage = {
          element: image,
          width: image.naturalWidth || image.width,
          height: image.naturalHeight || image.height
        };
        this.initializeAvatarCrop();
        this.updateAvatarPreview();
      };
      image.onerror = () => {
        URL.revokeObjectURL(objectUrl);
        ElementPlus.ElMessage.error('图片读取失败，请换一张图片。');
      };
      image.src = objectUrl;
    },
    initializeAvatarCrop() {
      if (!this.avatarImage) return;
      const minScale = Math.max(
        AVATAR_CROP_SIZE / this.avatarImage.width,
        AVATAR_CROP_SIZE / this.avatarImage.height
      );
      const scale = minScale;
      this.avatarCrop.minScale = minScale;
      this.avatarCrop.maxScale = minScale * 4;
      this.avatarCrop.scale = scale;
      this.avatarCrop.x = (AVATAR_CROP_SIZE - this.avatarImage.width * scale) / 2;
      this.avatarCrop.y = (AVATAR_CROP_SIZE - this.avatarImage.height * scale) / 2;
      this.constrainAvatarCrop();
    },
    constrainAvatarCrop() {
      if (!this.avatarImage) return;
      const width = this.avatarImage.width * this.avatarCrop.scale;
      const height = this.avatarImage.height * this.avatarCrop.scale;
      const minX = Math.min(0, AVATAR_CROP_SIZE - width);
      const minY = Math.min(0, AVATAR_CROP_SIZE - height);
      this.avatarCrop.x = Math.min(0, Math.max(minX, this.avatarCrop.x));
      this.avatarCrop.y = Math.min(0, Math.max(minY, this.avatarCrop.y));
    },
    setAvatarScale(value, centerX = AVATAR_CROP_SIZE / 2, centerY = AVATAR_CROP_SIZE / 2) {
      if (!this.avatarImage) return;
      const oldScale = this.avatarCrop.scale;
      const nextScale = Math.min(this.avatarCrop.maxScale, Math.max(this.avatarCrop.minScale, Number(value)));
      if (!Number.isFinite(nextScale) || nextScale <= 0) return;
      const imageCenterX = (centerX - this.avatarCrop.x) / oldScale;
      const imageCenterY = (centerY - this.avatarCrop.y) / oldScale;
      this.avatarCrop.scale = nextScale;
      this.avatarCrop.x = centerX - imageCenterX * nextScale;
      this.avatarCrop.y = centerY - imageCenterY * nextScale;
      this.constrainAvatarCrop();
      this.updateAvatarPreview();
    },
    handleAvatarWheel(event) {
      if (!this.avatarImage) return;
      const rect = event.currentTarget.getBoundingClientRect();
      const centerX = event.clientX - rect.left;
      const centerY = event.clientY - rect.top;
      const factor = event.deltaY > 0 ? 0.94 : 1.06;
      this.setAvatarScale(this.avatarCrop.scale * factor, centerX, centerY);
    },
    startAvatarDrag(event) {
      if (!this.avatarImage || event.button > 0) return;
      this.avatarCrop.dragging = true;
      this.avatarCrop.pointerId = event.pointerId;
      this.avatarCrop.startX = event.clientX;
      this.avatarCrop.startY = event.clientY;
      this.avatarCrop.originX = this.avatarCrop.x;
      this.avatarCrop.originY = this.avatarCrop.y;
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    moveAvatarDrag(event) {
      if (!this.avatarCrop.dragging || event.pointerId !== this.avatarCrop.pointerId) return;
      this.avatarCrop.x = this.avatarCrop.originX + event.clientX - this.avatarCrop.startX;
      this.avatarCrop.y = this.avatarCrop.originY + event.clientY - this.avatarCrop.startY;
      this.constrainAvatarCrop();
      this.updateAvatarPreview();
    },
    endAvatarDrag(event) {
      if (event.pointerId !== this.avatarCrop.pointerId) return;
      this.avatarCrop.dragging = false;
      this.avatarCrop.pointerId = null;
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
    },
    updateAvatarPreview() {
      if (!this.avatarImage) {
        this.avatarPreviewUrl = '';
        return;
      }
      this.avatarPreviewUrl = this.renderAvatarCanvas(160).toDataURL('image/png');
    },
    renderAvatarCanvas(size) {
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      const ratio = size / AVATAR_CROP_SIZE;
      ctx.drawImage(
        this.avatarImage.element,
        this.avatarCrop.x * ratio,
        this.avatarCrop.y * ratio,
        this.avatarImage.width * this.avatarCrop.scale * ratio,
        this.avatarImage.height * this.avatarCrop.scale * ratio
      );
      return canvas;
    },
    isValidHexColor(color) {
      return /^#[0-9a-f]{6}$/i.test(String(color || '').trim());
    },
    adminUserAvatarText(user) {
      if (!user) return '?';
      const source = user.nickname || user.name || '?';
      return source.trim().slice(0, 1).toUpperCase();
    },
    adminUserAvatarStyle(user) {
      const color = user && user.avatarColor ? String(user.avatarColor).toLowerCase() : '';
      return { background: this.isValidHexColor(color) ? color : DEFAULT_AVATAR_COLOR };
    },
    setAvatarColorDraft(color) {
      const nextColor = String(color || '').trim().toLowerCase();
      if (!this.isValidHexColor(nextColor)) return;
      this.avatarColorDraft = nextColor;
    },
    setAvatarRgbPart(part, value) {
      const channel = Math.min(255, Math.max(0, Number.parseInt(value, 10) || 0));
      const rgb = this.avatarDraftRgb;
      rgb[part] = channel;
      const hex = ['r', 'g', 'b']
        .map(key => rgb[key].toString(16).padStart(2, '0'))
        .join('');
      this.avatarColorDraft = `#${hex}`;
    },
    async saveAvatar() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录后再修改头像。');
        return;
      }
      if (!this.avatarCanSave) {
        ElementPlus.ElMessage.warning('请先选择图片或调整背景颜色。');
        return;
      }
      this.avatarLoading = true;
      try {
        if (this.avatarImage) {
          const dataUrl = this.renderAvatarCanvas(AVATAR_OUTPUT_SIZE).toDataURL('image/png');
          const base64 = dataUrl.split(',', 2)[1] || '';
          const byteLength = Math.ceil(base64.length * 3 / 4);
          if (byteLength > AVATAR_UPLOAD_MAX_BYTES) {
            throw new Error('裁剪后的头像不能超过 2MB。');
          }
          const payload = await this.apiJson(`${AUTH_API}/avatar`, {
            method: 'POST',
            body: JSON.stringify({
              filename: 'avatar.png',
              contentType: 'image/png',
              data: base64
            })
          });
          this.currentUser = payload.user;
        }
        if (this.avatarHasPendingColor) {
          const payload = await this.apiJson(`${AUTH_API}/avatar-color`, {
            method: 'PUT',
            body: JSON.stringify({ color: this.avatarDraftColor })
          });
          this.currentUser = payload.user;
        }
        this.avatarDialogVisible = false;
        this.resetAvatarDraft();
        ElementPlus.ElMessage.success('头像设置已保存。');
      } catch (error) {
        ElementPlus.ElMessage.error(`头像保存失败：${error.message}`);
      } finally {
        this.avatarLoading = false;
      }
    },
    async deleteAvatar() {
      if (!this.currentUser || !this.currentUser.avatarUrl) return;
      this.avatarLoading = true;
      try {
        const payload = await this.apiJson(`${AUTH_API}/avatar`, { method: 'DELETE' });
        this.currentUser = payload.user;
        this.resetAvatarDraft();
        ElementPlus.ElMessage.success('头像已移除。');
      } catch (error) {
        ElementPlus.ElMessage.error(`头像移除失败：${error.message}`);
      } finally {
        this.avatarLoading = false;
      }
    },
    async openFeedbackDialog() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录后再提交反馈。');
        return;
      }
      this.accountMenuOpen = false;
      this.feedbackDialogVisible = true;
      await this.loadFeedback();
    },
    async loadFeedback() {
      if (!this.currentUser) {
        this.feedbackItems = [];
        return;
      }
      this.feedbackLoading = true;
      try {
        const payload = await this.apiJson(FEEDBACK_API, { cache: 'no-store' });
        this.feedbackItems = Array.isArray(payload.feedback) ? payload.feedback : [];
        this.feedbackLimitPerUser = Number(payload.feedbackLimitPerUser || this.feedbackLimitPerUser);
      } catch (error) {
        ElementPlus.ElMessage.error(`反馈读取失败：${error.message}`);
      } finally {
        this.feedbackLoading = false;
      }
    },
    async submitFeedback() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录后再提交反馈。');
        return;
      }
      const content = this.feedbackForm.content.trim();
      if (!content) {
        ElementPlus.ElMessage.warning('反馈内容不能为空。');
        return;
      }
      if (this.pendingFeedbackCount >= this.feedbackLimitPerUser) {
        ElementPlus.ElMessage.warning(`每个用户未回复的反馈不能超过 ${this.feedbackLimitPerUser} 条。`);
        return;
      }
      this.feedbackLoading = true;
      try {
        await this.apiJson(FEEDBACK_API, {
          method: 'POST',
          body: JSON.stringify({ content })
        });
        this.feedbackForm.content = '';
        await this.loadFeedback();
        ElementPlus.ElMessage.success('反馈已提交。');
      } catch (error) {
        ElementPlus.ElMessage.error(`反馈提交失败：${error.message}`);
      } finally {
        this.feedbackLoading = false;
      }
    },
    deleteFeedback(item) {
      if (!this.currentUser || !item) return;
      ElementPlus.ElMessageBox.confirm(
        '确定删除这条反馈？删除后管理员回复也会一起移除。',
        '删除反馈',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        this.feedbackLoading = true;
        try {
          await this.apiJson(`${FEEDBACK_API}/${encodeURIComponent(item.id)}`, { method: 'DELETE' });
          await this.loadFeedback();
          ElementPlus.ElMessage.success('反馈已删除。');
        } catch (error) {
          ElementPlus.ElMessage.error(`反馈删除失败：${error.message}`);
        } finally {
          this.feedbackLoading = false;
        }
      }).catch(() => {});
    },
    feedbackStatusLabel(status) {
      return status === 'replied' ? '已回复' : '待回复';
    },
    feedbackStatusType(status) {
      return status === 'replied' ? 'success' : 'warning';
    },
    async logout() {
      if (this.authToken) {
        await this.apiJson(`${AUTH_API}/logout`, { method: 'POST' }).catch(() => {});
      }
      this.authToken = '';
      this.currentUser = null;
      this.adminMode = false;
      this.adminSection = 'users';
      this.adminUsers = [];
      this.adminUsersPage = 1;
      this.adminSelectedUserId = '';
      this.adminEditingUserId = '';
      this.adminEditingName = '';
      this.adminLogs = [];
      this.adminLogsTotal = 0;
      this.adminFeedback = [];
      this.adminFeedbackTotal = 0;
      this.adminFeedbackLimitDraft = 10;
      this.adminFeedbackReplyVisible = false;
      this.adminFeedbackActive = null;
      this.adminFeedbackReply = '';
      this.adminTrafficView = '7d';
      this.adminTrafficHoverPoint = null;
      this.adminTrafficRecentTotal = 0;
      this.adminTrafficRecentPage = 1;
      this.adminTraffic = {
        seriesUnit: 'day',
        totalVisits: 0,
        todayVisits: 0,
        uniqueIps: 0,
        todayUniqueIps: 0,
        trendSeries: [],
        dailySeries: [],
        topIps: [],
        recentVisits: []
      };
      this.adminAiUsageView = '7d';
      this.adminAiUsageHoverPoint = null;
      this.adminAiUsageUsersTotal = 0;
      this.adminAiUsagePage = 1;
      this.adminAiGlobalLimitDraft = {
        windowHours: 24,
        inputTokenLimit: 200000,
        outputTokenLimit: 50000
      };
      this.adminAiUserLimitDrafts = {};
      this.adminAiUsage = {
        seriesUnit: 'day',
        globalLimit: {
          windowHours: 24,
          inputTokenLimit: 200000,
          outputTokenLimit: 50000
        },
        totalPromptTokens: 0,
        totalCompletionTokens: 0,
        totalCalls: 0,
        todayPromptTokens: 0,
        todayCompletionTokens: 0,
        todayCalls: 0,
        trendSeries: [],
        users: []
      };
      this.nicknameDialogVisible = false;
      this.nicknameForm.nickname = '';
      this.passwordDialogVisible = false;
      this.passwordForm = { currentPassword: '', newPassword: '', confirmPassword: '' };
      this.avatarDialogVisible = false;
      this.resetAvatarDraft();
      this.resetSubjectTemplateState();
      this.feedbackDialogVisible = false;
      this.feedbackForm.content = '';
      this.feedbackItems = [];
      this.feedbackLimitPerUser = 10;
      this.adminTimelineLoadedUserId = '';
      this.tasks = [];
      this.scheduleItems = [];
      this.habits = [];
      this.aiChatOpen = false;
      this.aiChatMessages = [];
      this.aiChatInput = '';
      this.aiPendingActions = [];
      this.aiActionResults = [];
      this.aiApprovalVisible = false;
      this.aiCurrentActionIndex = 0;
      this.aiExecutingActionId = '';
      this.habitSyncConflicts = [];
      this.scheduleTemplateVersions = [];
      this.scheduleDayOverrides = {};
      this.accountMenuOpen = true;
      localStorage.removeItem(AUTH_TOKEN_KEY);
      ElementPlus.ElMessage.success('已退出登录。');
    },
    async loadTasks() {
      if (!this.currentUser) {
        this.tasks = [];
        return;
      }
      try {
        const response = await fetch(TASKS_API, { cache: 'no-store', headers: this.authHeaders() });
        if (!response.ok) throw new Error('服务器读取失败');
        const payload = await response.json();
        const serverTasks = Array.isArray(payload.tasks) ? payload.tasks.map(task => this.normalizeTaskPool(task)) : [];
        this.tasks = serverTasks;
      } catch (error) {
        console.error('读取服务器任务失败：', error);
        this.tasks = [];
        ElementPlus.ElMessage.error('任务数据读取失败，请检查服务是否正常运行。');
      }
    },
    async loadScheduleItems() {
      if (!this.currentUser) {
        this.scheduleItems = [];
        return;
      }
      try {
        const range = this.scheduleSyncRange();
        const payload = await this.apiJson(`${SCHEDULE_API}?from=${encodeURIComponent(range.from)}&to=${encodeURIComponent(range.to)}`, { cache: 'no-store' });
        this.scheduleItems = Array.isArray(payload.items) ? payload.items : [];
        this.habitSyncConflicts = Array.isArray(payload.habitSyncConflicts) ? payload.habitSyncConflicts : [];
      } catch (error) {
        console.error('读取每日安排失败：', error);
        ElementPlus.ElMessage.error('每日安排读取失败。');
      }
    },
    async loadHabits() {
      if (!this.currentUser) {
        this.habits = [];
        return;
      }
      try {
        const payload = await this.apiJson(HABITS_API, { cache: 'no-store' });
        this.habits = Array.isArray(payload.habits) ? payload.habits : [];
      } catch (error) {
        console.error('读取习惯失败：', error);
        ElementPlus.ElMessage.error('习惯数据读取失败。');
      }
    },
    async loadScheduleConfig() {
      try {
        const payload = await this.apiJson(SCHEDULE_CONFIG_API, { cache: 'no-store' });
        this.defaultWeekSlots = this.cloneSlots(payload.defaultWeekSlots || DEFAULT_WEEK_SLOTS);
        this.scheduleTemplateVersions = Array.isArray(payload.templateVersions) ? payload.templateVersions : [];
        this.scheduleDayOverrides = payload.dayOverrides && typeof payload.dayOverrides === 'object' ? payload.dayOverrides : {};
      } catch (error) {
        console.error('读取时间格子配置失败：', error);
        this.defaultWeekSlots = this.cloneSlots(DEFAULT_WEEK_SLOTS);
        this.scheduleTemplateVersions = [];
        this.scheduleDayOverrides = {};
      }
    },
    cloneSlots(value) {
      return JSON.parse(JSON.stringify(value || {}));
    },
    taskPool(task) {
      if (task && task.pool === 'arrangement') return 'arrangement';
      if (task && task.pool === 'habit') return 'habit';
      if (task && task.pool === 'schedule') return 'schedule';
      return 'todo';
    },
    normalizeTaskPool(task) {
      const pool = task && ['arrangement', 'habit', 'schedule'].includes(task.pool) ? task.pool : 'todo';
      return { ...task, pool };
    },
    normalizeWeekSlots(value) {
      const source = value || {};
      return ['0', '1', '2', '3', '4', '5', '6'].reduce((week, key) => {
        week[key] = this.cloneSlots(source[key] || []);
        return week;
      }, {});
    },
    weekTemplateForDate(dateKey) {
      // Template versions are append-only; the latest version before dateKey wins.
      const versions = [...this.scheduleTemplateVersions]
        .filter(version => version.effectiveFrom <= dateKey)
        .sort((a, b) => {
          if (a.effectiveFrom !== b.effectiveFrom) return a.effectiveFrom.localeCompare(b.effectiveFrom);
          return Number(a.id || 0) - Number(b.id || 0);
        });
      const latest = versions[versions.length - 1];
      return this.normalizeWeekSlots(latest ? latest.slots : this.defaultWeekSlots);
    },
    slotsForDate(dateKey) {
      // A single-day override always takes priority over the weekly template.
      if (this.scheduleDayOverrides[dateKey]) return this.sortSlots(this.cloneSlots(this.scheduleDayOverrides[dateKey]));
      const weekday = String(new Date(`${dateKey}T00:00:00`).getDay());
      return this.sortSlots(this.weekTemplateForDate(dateKey)[weekday] || []);
    },
    sortSlots(slots) {
      return [...(slots || [])].sort((a, b) => {
        const startDiff = String(a.start || '').localeCompare(String(b.start || ''));
        if (startDiff !== 0) return startDiff;
        return String(a.end || '').localeCompare(String(b.end || ''));
      });
    },
    scheduleSlotKeyFromBase(date, keyBase) {
      return `${date}-${keyBase}`;
    },
    minutesBetween(start, end) {
      const [sh, sm] = start.split(':').map(Number);
      const [eh, em] = end.split(':').map(Number);
      return (eh * 60 + em) - (sh * 60 + sm);
    },
    scheduleItemsForSlot(date, slotKey) {
      return this.scheduleItemsBySlot[this.scheduleSlotKey(date, slotKey)] || [];
    },
    visibleScheduleItemsForSlot(date, slotKey) {
      return this.scheduleItemsForSlot(date, slotKey)
        .filter(item => this.showCompleted || !item.completed);
    },
    slotUsedMinutes(date, slotKey, excludeId = null) {
      return this.scheduleItemsForSlot(date, slotKey)
        .filter(item => item.id !== excludeId)
        .reduce((sum, item) => sum + Number(item.durationMinutes || 0), 0);
    },
    scheduleSlotKey(date, slotKey) {
      return `${date}::${slotKey}`;
    },
    scheduleSortValue(item) {
      const value = Number(item && item.sortOrder);
      return Number.isFinite(value) ? value : 0;
    },
    compareScheduleItems(a, b) {
      const sortDiff = this.scheduleSortValue(a) - this.scheduleSortValue(b);
      if (sortDiff !== 0) return sortDiff;
      return String(a.createdAt || '').localeCompare(String(b.createdAt || ''));
    },
    prepareScheduleDragEvent(event, id) {
      if (!event || !event.dataTransfer) return;
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', id);
    },
    startTaskDrag(task, event = null) {
      if (this.adminMode) return;
      if (this.activePage !== 'daily') return;
      this.prepareScheduleDragEvent(event, task.id);
      this.draggedTaskId = task.id;
      this.draggedScheduleItemId = null;
      this.scheduleDropPosition = null;
    },
    startScheduleDrag(item, event = null) {
      if (this.adminMode) return;
      if (this.activePage !== 'daily') return;
      if (item && item.habitId) return;
      this.prepareScheduleDragEvent(event, item.id);
      this.draggedScheduleItemId = item.id;
      this.draggedTaskId = null;
      this.scheduleDropPosition = null;
    },
    startTaskPointerDrag(task, event) {
      this.startSchedulePointerDrag('task', task.id, event);
    },
    startSchedulePointerDragForItem(item, event) {
      if (item && item.habitId) return;
      this.startSchedulePointerDrag('schedule', item.id, event);
    },
    buildScheduleDragPreview(type, id, sourceElement, event) {
      const rect = sourceElement && sourceElement.getBoundingClientRect
        ? sourceElement.getBoundingClientRect()
        : null;
      const width = rect ? Math.min(rect.width, 280) : 240;
      const offsetX = rect ? event.clientX - rect.left : Math.min(28, width / 2);
      const offsetY = rect ? event.clientY - rect.top : 24;
      let task = null;
      let durationText = '';
      let completed = false;
      if (type === 'schedule') {
        const item = this.scheduleItems.find(entry => entry.id === id);
        if (!item) return null;
        task = item.task || this.tasks.find(taskItem => taskItem.id === item.taskId);
        durationText = `${item.durationMinutes} 分钟`;
        completed = !!item.completed;
      } else {
        task = this.tasks.find(item => item.id === id);
        completed = !!(task && task.completed);
      }
      if (!task) return null;
      const metaItems = [];
      if (task.subject) metaItems.push(task.subject);
      if (durationText) metaItems.push(durationText);
      if (task.dueAt) metaItems.push(`${this.formatDateLabel(task.dueAt)} ${this.formatTime(task.dueAt)}`);
      metaItems.push(this.priorityLabel(task.priority));
      if (completed) metaItems.push('已完成');
      return {
        type,
        title: task.title,
        note: task.note || '',
        priority: task.priority,
        completed,
        metaItems,
        width,
        offsetX,
        offsetY,
        x: event.clientX - offsetX,
        y: event.clientY - offsetY
      };
    },
    moveScheduleDragPreview(clientX, clientY) {
      if (!this.scheduleDragPreview) return;
      const x = clientX - this.scheduleDragPreview.offsetX;
      const y = clientY - this.scheduleDragPreview.offsetY;
      const previewElement = this.$refs.scheduleDragPreview;
      if (previewElement) {
        previewElement.style.transform = `translate3d(${x}px, ${y}px, 0)`;
        return;
      }
      this.scheduleDragPreview.x = x;
      this.scheduleDragPreview.y = y;
    },
    showScheduleDragPreview(drag) {
      if (!drag || !drag.preview) return;
      this.scheduleDragPreview = {
        ...drag.preview,
        x: drag.clientX - drag.preview.offsetX,
        y: drag.clientY - drag.preview.offsetY
      };
    },
    scheduleDragPreviewClass() {
      if (!this.scheduleDragPreview) return '';
      return [
        this.priorityClass(this.scheduleDragPreview.priority),
        {
          completed: this.scheduleDragPreview.completed,
          'is-schedule-preview': this.scheduleDragPreview.type === 'schedule'
        }
      ];
    },
    scheduleDragPreviewStyle() {
      if (!this.scheduleDragPreview) return {};
      return {
        width: `${this.scheduleDragPreview.width}px`,
        transform: `translate3d(${this.scheduleDragPreview.x}px, ${this.scheduleDragPreview.y}px, 0)`
      };
    },
    startSchedulePointerDrag(type, id, event) {
      if (this.adminMode || this.activePage !== 'daily') return;
      if (!event || event.pointerType === 'mouse' || event.button !== 0) return;
      this.schedulePointerDrag = {
        type,
        id,
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        clientX: event.clientX,
        clientY: event.clientY,
        dragging: false,
        preview: this.buildScheduleDragPreview(type, id, event.currentTarget, event)
      };
      window.addEventListener('pointermove', this.handleSchedulePointerMove, { passive: false });
      window.addEventListener('pointerup', this.finishSchedulePointerDrag, { passive: false });
      window.addEventListener('pointercancel', this.cancelSchedulePointerDrag, { passive: false });
    },
    handleSchedulePointerMove(event) {
      const drag = this.schedulePointerDrag;
      if (!drag || event.pointerId !== drag.pointerId) return;
      drag.clientX = event.clientX;
      drag.clientY = event.clientY;
      const distance = Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY);
      if (!drag.dragging && distance < 8) return;
      event.preventDefault();
      if (!drag.dragging) {
        drag.dragging = true;
        document.body.classList.add('is-schedule-touch-dragging');
        if (drag.type === 'task') {
          this.draggedTaskId = drag.id;
          this.draggedScheduleItemId = null;
        } else {
          this.draggedScheduleItemId = drag.id;
          this.draggedTaskId = null;
        }
        this.scheduleDropPosition = null;
        this.showScheduleDragPreview(drag);
      }
      this.moveScheduleDragPreview(event.clientX, event.clientY);
      const slotElement = this.scheduleSlotElementFromPoint(event.clientX, event.clientY);
      const context = this.scheduleSlotContextFromElement(slotElement);
      if (!context) {
        if (this.scheduleDropPosition) this.scheduleDropPosition = null;
        return;
      }
      this.updateScheduleDropPosition({
        currentTarget: slotElement,
        clientY: event.clientY
      }, context.day, context.slot);
    },
    finishSchedulePointerDrag(event) {
      const drag = this.schedulePointerDrag;
      if (!drag || event.pointerId !== drag.pointerId) return;
      if (drag.dragging) {
        event.preventDefault();
        const slotElement = this.scheduleSlotElementFromPoint(event.clientX, event.clientY);
        const context = this.scheduleSlotContextFromElement(slotElement);
        if (context) {
          this.handleDropOnSlot({
            currentTarget: slotElement,
            clientY: event.clientY
          }, context.day, context.slot);
        } else {
          this.clearScheduleDragState();
        }
        this.suppressNextScheduleClick = true;
        window.setTimeout(() => {
          this.suppressNextScheduleClick = false;
        }, 200);
      }
      this.schedulePointerDrag = null;
      this.scheduleDragPreview = null;
      document.body.classList.remove('is-schedule-touch-dragging');
      this.removeSchedulePointerListeners();
    },
    cancelSchedulePointerDrag(event = null) {
      const drag = this.schedulePointerDrag;
      if (event && drag && event.pointerId !== drag.pointerId) return;
      this.schedulePointerDrag = null;
      this.scheduleDragPreview = null;
      document.body.classList.remove('is-schedule-touch-dragging');
      this.removeSchedulePointerListeners();
      this.clearScheduleDragState();
    },
    removeSchedulePointerListeners() {
      window.removeEventListener('pointermove', this.handleSchedulePointerMove);
      window.removeEventListener('pointerup', this.finishSchedulePointerDrag);
      window.removeEventListener('pointercancel', this.cancelSchedulePointerDrag);
    },
    scheduleSlotElementFromPoint(clientX, clientY) {
      const element = document.elementFromPoint(clientX, clientY);
      return element ? element.closest('.schedule-slot') : null;
    },
    scheduleSlotContextFromElement(slotElement) {
      if (!slotElement) return null;
      const date = slotElement.dataset.scheduleDate;
      const slotKey = slotElement.dataset.scheduleSlotKey;
      if (!date || !slotKey) return null;
      const day = this.scheduleDayColumns.find(item => item.key === date);
      const slot = day ? day.slots.find(item => item.key === slotKey) : null;
      return day && slot ? { day, slot } : null;
    },
    openTaskFromPointerClick(task) {
      if (this.suppressNextScheduleClick) return;
      this.openEditDialog(task);
    },
    openScheduleFromPointerClick(item) {
      if (this.suppressNextScheduleClick) return;
      this.openScheduleEditDialog(item);
    },
    clearScheduleDragState() {
      this.draggedTaskId = null;
      this.draggedScheduleItemId = null;
      this.scheduleDropPosition = null;
      this.scheduleDragPreview = null;
    },
    hasActiveScheduleDrag() {
      return !!(this.draggedTaskId || this.draggedScheduleItemId);
    },
    scheduleDropKey(date, slotKey) {
      return `${date}::${slotKey}`;
    },
    isScheduleDropPosition(day, slot) {
      return this.scheduleDropPosition
        && this.scheduleDropPosition.key === this.scheduleDropKey(day.key, slot.key);
    },
    isScheduleInsertIndex(day, slot, index) {
      return this.isScheduleDropPosition(day, slot)
        && this.scheduleDropPosition.index === index;
    },
    updateScheduleDropPosition(event, day, slot) {
      if (this.adminMode || !this.hasActiveScheduleDrag()) return;
      const slotElement = event.currentTarget;
      if (!slotElement) return;
      const cards = Array.from(slotElement.querySelectorAll('.schedule-card'))
        .filter(card => String(card.dataset.scheduleId) !== String(this.draggedScheduleItemId));
      let index = cards.length;
      if (cards.length) {
        const targetIndex = cards.findIndex((card) => {
          const rect = card.getBoundingClientRect();
          return event.clientY < rect.top + (rect.height / 2);
        });
        index = targetIndex < 0 ? cards.length : targetIndex;
      }
      const key = this.scheduleDropKey(day.key, slot.key);
      if (this.scheduleDropPosition
        && this.scheduleDropPosition.key === key
        && this.scheduleDropPosition.index === index) {
        return;
      }
      this.scheduleDropPosition = {
        key,
        date: day.key,
        slotKey: slot.key,
        index
      };
    },
    dropIndexForSlot(event, day, slot) {
      if (!this.isScheduleDropPosition(day, slot)) {
        this.updateScheduleDropPosition(event, day, slot);
      }
      return this.isScheduleDropPosition(day, slot)
        ? this.scheduleDropPosition.index
        : this.scheduleItemsForSlot(day.key, slot.key).length;
    },
    handleDropOnSlot(event, day, slot) {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再创建安排。');
        this.clearScheduleDragState();
        return;
      }
      const dropIndex = this.dropIndexForSlot(event, day, slot);
      if (this.draggedScheduleItemId) {
        this.moveScheduleItemToSlot(day, slot, dropIndex);
        return;
      }
      if (this.draggedTaskId) {
        this.openScheduleCreateDialog(day, slot, dropIndex);
      }
    },
    openDirectScheduleCreateDialog() {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再新增安排。');
        return;
      }
      const dateKey = this.pageViewDateKeys.daily || this.currentViewDateKey || this.formatDateKey(new Date());
      this.ensureDateRangeForKey(dateKey);
      this.scheduleDialogMode = 'create';
      this.activeScheduleItemId = null;
      this.activeScheduleTask = null;
      this.activeScheduleSlot = null;
      this.activeScheduleSortOrder = null;
      this.scheduleForm = { ...this.emptyScheduleForm(), date: dateKey };
      this.scheduleDialogVisible = true;
    },
    applyDirectScheduleSlot(slot) {
      const dateKey = this.scheduleForm.date || this.formatDateKey(new Date());
      this.activeScheduleSlot = {
        ...slot,
        key: this.scheduleSlotKeyFromBase(dateKey, slot.keyBase),
        date: dateKey,
        dateLabel: this.formatDateLabel(this.parseDateKey(dateKey))
      };
      this.scheduleForm.durationMinutes = Math.min(Number(this.scheduleForm.durationMinutes || 30), slot.duration);
    },
    handleDirectScheduleDateChange() {
      if (!this.scheduleForm.date) {
        this.activeScheduleSlot = null;
        return;
      }
      const expanded = this.ensureDateRangeForKey(this.scheduleForm.date);
      if (expanded && this.currentUser) this.loadScheduleItems();
      if (!this.scheduleForm.slotKeyBase) {
        this.activeScheduleSlot = null;
        return;
      }
      const slot = this.directScheduleSlotOptions.find(item => item.keyBase === this.scheduleForm.slotKeyBase);
      if (slot) {
        this.applyDirectScheduleSlot(slot);
        return;
      }
      this.scheduleForm.slotKeyBase = '';
      this.activeScheduleSlot = null;
    },
    handleDirectScheduleSlotChange(keyBase) {
      const slot = this.directScheduleSlotOptions.find(item => item.keyBase === keyBase);
      if (!slot) {
        this.activeScheduleSlot = null;
        return;
      }
      this.applyDirectScheduleSlot(slot);
    },
    openScheduleCreateDialog(day, slot, dropIndex = null) {
      const task = this.tasks.find(item => item.id === this.draggedTaskId);
      if (!task) return;
      const remaining = slot.duration - this.slotUsedMinutes(day.key, slot.key);
      if (remaining <= 0) {
        ElementPlus.ElMessage.warning('这个时间格子已经排满了。');
        this.clearScheduleDragState();
        return;
      }
      this.scheduleDialogMode = 'create';
      this.activeScheduleItemId = null;
      this.activeScheduleTask = task;
      this.activeScheduleSlot = { ...slot, date: day.key, dateLabel: day.label };
      this.activeScheduleSortOrder = Number.isInteger(dropIndex)
        ? this.sortOrderForIndex(day.key, slot.key, null, dropIndex)
        : null;
      this.scheduleForm = { ...this.emptyScheduleForm(), date: day.key, durationMinutes: Math.min(30, remaining) };
      this.scheduleDialogVisible = true;
      this.clearScheduleDragState();
    },
    sortOrderForIndex(date, slotKey, draggedId, dropIndex) {
      const items = this.scheduleItemsForSlot(date, slotKey)
        .filter(item => item.id !== draggedId)
        .sort((a, b) => this.compareScheduleItems(a, b));
      const index = Math.max(0, Math.min(Number(dropIndex || 0), items.length));
      const next = items[index];
      const prev = items[index - 1];
      if (!prev && !next) return 1024;
      if (!prev) return this.scheduleSortValue(next) - 1024;
      if (!next) return this.scheduleSortValue(prev) + 1024;
      return (this.scheduleSortValue(prev) + this.scheduleSortValue(next)) / 2;
    },
    async moveScheduleItemToSlot(day, slot, dropIndex) {
      const item = this.scheduleItems.find(entry => entry.id === this.draggedScheduleItemId);
      if (!item) {
        this.clearScheduleDragState();
        return;
      }
      const sortOrder = this.sortOrderForIndex(day.key, slot.key, item.id, dropIndex);
      const payload = {
        date: day.key,
        slotKey: slot.key,
        slotLabel: slot.label,
        slotStart: slot.start,
        slotEnd: slot.end,
        durationMinutes: item.durationMinutes,
        sortOrder,
        note: item.note || '',
        completed: !!item.completed
      };
      try {
        await this.apiJson(`${SCHEDULE_API}/${item.id}`, { method: 'PUT', body: JSON.stringify(payload) });
        await this.loadScheduleItems();
        ElementPlus.ElMessage.success('安排已调整。');
      } catch (error) {
        ElementPlus.ElMessage.error(`调整失败：${error.message}`);
      } finally {
        this.clearScheduleDragState();
      }
    },
    openScheduleEditDialog(item) {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再编辑安排。');
        return;
      }
      const task = this.tasks.find(taskItem => taskItem.id === item.taskId) || item.task;
      this.scheduleDialogMode = 'edit';
      this.activeScheduleItemId = item.id;
      this.activeScheduleTask = task;
      this.activeScheduleSortOrder = null;
      this.activeScheduleSlot = {
        key: item.slotKey,
        label: item.slotLabel,
        start: item.slotStart,
        end: item.slotEnd,
        duration: this.minutesBetween(item.slotStart, item.slotEnd),
        date: item.date,
        dateLabel: item.date
      };
      this.scheduleForm = {
        ...this.emptyScheduleForm(),
        durationMinutes: Number(item.durationMinutes || 1),
        date: item.date,
        note: item.note || '',
        completed: !!item.completed
      };
      this.scheduleDialogVisible = true;
    },
    async saveScheduleItem() {
      if (!this.currentUser) return;
      let scheduleTask = this.activeScheduleTask;
      if (this.isDirectScheduleCreate) {
        const title = this.scheduleForm.title.trim();
        const subject = this.scheduleForm.subject.trim();
        if (!title || !subject || !this.scheduleForm.date || !this.scheduleForm.slotKeyBase || !this.activeScheduleSlot) {
          ElementPlus.ElMessage.warning('请填写标题、科目、日期和时间段。');
          return;
        }
        if (subject.length > 40) {
          ElementPlus.ElMessage.warning('科目不能超过 40 个字符。');
          return;
        }
      } else if (!scheduleTask || !this.activeScheduleSlot) {
        return;
      }
      const used = this.slotUsedMinutes(
        this.activeScheduleSlot.date,
        this.activeScheduleSlot.key,
        this.scheduleDialogMode === 'edit' ? this.activeScheduleItemId : null
      );
      const duration = Number(this.scheduleForm.durationMinutes || 0);
      if (!Number.isFinite(duration) || duration <= 0) {
        ElementPlus.ElMessage.warning('预计持续时间必须大于 0。');
        return;
      }
      if (used + duration > this.activeScheduleSlot.duration) {
        ElementPlus.ElMessage.error(`时间段容量不足：已用 ${used} 分钟，总共 ${this.activeScheduleSlot.duration} 分钟。`);
        return;
      }
      let createdDirectTask = null;
      const payload = {
        taskId: scheduleTask ? scheduleTask.id : '',
        date: this.activeScheduleSlot.date,
        slotKey: this.activeScheduleSlot.key,
        slotLabel: this.activeScheduleSlot.label,
        slotStart: this.activeScheduleSlot.start,
        slotEnd: this.activeScheduleSlot.end,
        durationMinutes: duration,
        note: this.scheduleForm.note.trim(),
        completed: !!this.scheduleForm.completed
      };
      if (this.activeScheduleSortOrder !== null) {
        payload.sortOrder = this.activeScheduleSortOrder;
      }
      try {
        if (this.isDirectScheduleCreate) {
          const taskPayload = {
            id: this.createTaskId(),
            title: this.scheduleForm.title.trim(),
            subject: this.scheduleForm.subject.trim(),
            dueAt: '',
            pool: 'schedule',
            priority: this.scheduleForm.priority,
            note: '',
            completed: false,
            createdAt: new Date().toISOString()
          };
          createdDirectTask = await this.createTaskOnServer(taskPayload);
          scheduleTask = this.normalizeTaskPool(createdDirectTask || taskPayload);
          payload.taskId = scheduleTask.id;
        }
        if (this.scheduleDialogMode === 'create') {
          await this.apiJson(SCHEDULE_API, { method: 'POST', body: JSON.stringify(payload) });
          if (createdDirectTask) this.tasks = [...this.tasks, this.normalizeTaskPool(createdDirectTask)];
          ElementPlus.ElMessage.success('安排已创建。');
        } else {
          await this.apiJson(`${SCHEDULE_API}/${this.activeScheduleItemId}`, { method: 'PUT', body: JSON.stringify(payload) });
          ElementPlus.ElMessage.success('安排已更新。');
        }
        this.scheduleDialogVisible = false;
        this.activeScheduleSortOrder = null;
        await this.loadScheduleItems();
      } catch (error) {
        if (createdDirectTask && createdDirectTask.id) {
          this.deleteTaskOnServer(createdDirectTask.id).catch(() => {});
        }
        ElementPlus.ElMessage.error(`保存失败：${error.message}`);
      }
    },
    async toggleScheduleComplete() {
      this.scheduleForm.completed = !this.scheduleForm.completed;
      await this.saveScheduleItem();
    },
    deleteScheduleItem() {
      if (!this.activeScheduleItemId) return;
      ElementPlus.ElMessageBox.confirm('删除这个安排？不会删除原任务。', '删除安排', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await this.apiJson(`${SCHEDULE_API}/${this.activeScheduleItemId}`, { method: 'DELETE' });
          this.scheduleDialogVisible = false;
          await this.loadScheduleItems();
          ElementPlus.ElMessage.success('安排已删除。');
        } catch (error) {
          ElementPlus.ElMessage.error(`删除失败：${error.message}`);
        }
      }).catch(() => {});
    },
    openDaySlotEditor(day) {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再修改时间格子。');
        return;
      }
      this.slotEditorMode = 'day';
      this.slotEditorDate = day.key;
      this.slotEditorSlots = this.cloneSlots(this.slotsForDate(day.key));
      this.slotEditorVisible = true;
    },
    openWeekSlotEditor() {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再修改时间格子。');
        return;
      }
      const dateKey = this.pageViewDateKeys.daily || this.currentViewDateKey || this.formatDateKey(new Date());
      this.slotEditorMode = 'week';
      this.slotEditorDate = dateKey;
      this.slotEditorWeekday = String(new Date(`${dateKey}T00:00:00`).getDay());
      this.slotEditorWeekSlots = this.weekTemplateForDate(dateKey);
      this.slotEditorVisible = true;
    },
    addEditorSlot() {
      const slot = { keyBase: this.createSlotKeyBase(), label: '新时间段', start: '09:00', end: '10:00' };
      if (this.slotEditorMode === 'day') {
        this.slotEditorSlots.push(slot);
        return;
      }
      this.slotEditorWeekSlots[this.slotEditorWeekday].push(slot);
    },
    removeEditorSlot(index) {
      if (this.slotEditorMode === 'day') {
        this.slotEditorSlots.splice(index, 1);
        return;
      }
      this.slotEditorWeekSlots[this.slotEditorWeekday].splice(index, 1);
    },
    activeEditorSlots() {
      return this.slotEditorMode === 'day'
        ? this.slotEditorSlots
        : (this.slotEditorWeekSlots[this.slotEditorWeekday] || []);
    },
    validateEditorSlots(slots) {
      for (const slot of slots) {
        if (!slot.label || !slot.start || !slot.end) return '请填写每个时间段的名称、开始和结束时间。';
        slot.start = this.normalizeTimeText(slot.start);
        slot.end = this.normalizeTimeText(slot.end);
        if (!slot.start || !slot.end) return '时间格式必须是 H:mm 或 HH:mm，例如 9:00 或 18:40。';
        if (this.minutesBetween(slot.start, slot.end) <= 0) return '每个时间段的结束时间必须晚于开始时间。';
      }
      return '';
    },
    isValidTimeText(value) {
      return !!this.normalizeTimeText(value);
    },
    normalizeTimeText(value) {
      const match = String(value || '').trim().match(/^(\d{1,2}):(\d{2})$/);
      if (!match) return '';
      const hour = Number(match[1]);
      const minute = Number(match[2]);
      if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return '';
      return `${this.pad(hour)}:${this.pad(minute)}`;
    },
    setDialogTimePart(part, value) {
      const raw = String(value || '');
      const [hour = '', minute = ''] = String(this.form.time || '').split(':');
      if (raw.includes(':')) {
        const [rawHour = '', rawMinute = ''] = raw.split(':');
        const nextHour = rawHour.replace(/\D/g, '').slice(0, 2);
        const nextMinute = rawMinute.replace(/\D/g, '').slice(0, 2);
        this.form.time = nextHour || nextMinute ? `${nextHour}:${nextMinute}` : '';
        if (nextHour.length >= 2) this.focusDialogTimePart('minute');
        return;
      }

      const digits = raw.replace(/\D/g, '');
      if (part === 'hour') {
        const nextHour = digits.slice(0, 2);
        const nextMinute = digits.length > 2 ? digits.slice(2, 4) : minute;
        this.form.time = nextHour || nextMinute ? `${nextHour}:${nextMinute}` : '';
        if (digits.length >= 2) this.focusDialogTimePart('minute', true);
        return;
      }

      const nextMinute = digits.slice(0, 2);
      this.form.time = hour || nextMinute ? `${hour}:${nextMinute}` : '';
    },
    focusDialogTimeContainer(event) {
      if (event && event.target && event.target.closest && event.target.closest('.el-input')) return;
      this.focusDialogTimePart(String(this.dueHour || '').length >= 2 ? 'minute' : 'hour', true);
    },
    focusDialogTimePart(part, select = false) {
      const refName = part === 'minute' ? 'dueMinuteInput' : 'dueHourInput';
      this.$nextTick(() => {
        const inputRef = this.$refs[refName];
        if (!inputRef) return;
        if (inputRef.focus) inputRef.focus();
        const input = inputRef.input || (inputRef.$el && inputRef.$el.querySelector('input'));
        if (input && input.focus) input.focus();
        if (select && input && input.select) input.select();
      });
    },
    selectDialogTimeInput(event) {
      const input = event && event.target;
      if (!input || !input.select) return;
      window.setTimeout(() => {
        if (document.activeElement === input) input.select();
      }, 0);
    },
    handleDialogTimeKeydown(part, event) {
      const input = event.target;
      const value = String(input && input.value ? input.value : '');
      const selectionStart = input && typeof input.selectionStart === 'number' ? input.selectionStart : value.length;
      const selectionEnd = input && typeof input.selectionEnd === 'number' ? input.selectionEnd : value.length;
      if (part === 'hour' && (event.key === ':' || event.key === 'ArrowRight') && selectionStart === value.length && selectionEnd === value.length) {
        if (event.key === ':') event.preventDefault();
        this.focusDialogTimePart('minute', true);
        return;
      }
      if (part === 'minute' && (event.key === 'Backspace' || event.key === 'ArrowLeft') && selectionStart === 0 && selectionEnd === 0) {
        if (event.key === 'Backspace' && value) return;
        this.focusDialogTimePart('hour');
      }
    },
    normalizeDialogTimeInput() {
      const [rawHour = '', rawMinute = ''] = String(this.form.time || '').split(':');
      const hour = rawHour.replace(/\D/g, '').slice(0, 2);
      const minute = rawMinute.replace(/\D/g, '').slice(0, 2);
      if (!hour && !minute) {
        this.form.time = '';
        return;
      }
      const normalizedHour = hour && Number(hour) <= 23 ? this.pad(Number(hour)) : hour;
      const normalizedMinute = minute && Number(minute) <= 59 ? this.pad(Number(minute)) : minute;
      this.form.time = `${normalizedHour}:${normalizedMinute}`;
    },
    async saveSlotEditor() {
      if (!this.currentUser) return;
      const error = this.slotEditorMode === 'day'
        ? this.validateEditorSlots(this.slotEditorSlots)
        : ['0', '1', '2', '3', '4', '5', '6'].map(key => this.validateEditorSlots(this.slotEditorWeekSlots[key] || [])).find(Boolean);
      if (error) {
        ElementPlus.ElMessage.error(error);
        return;
      }
      try {
        if (this.slotEditorMode === 'day') {
          this.slotEditorSlots = this.sortSlots(this.slotEditorSlots);
          await this.apiJson(`${SCHEDULE_DAY_SLOTS_API}/${this.slotEditorDate}`, {
            method: 'PUT',
            body: JSON.stringify({ slots: this.slotEditorSlots })
          });
          ElementPlus.ElMessage.success('当天时间格子已保存。');
        } else {
          this.slotEditorWeekSlots = ['0', '1', '2', '3', '4', '5', '6'].reduce((week, key) => {
            week[key] = this.sortSlots(this.slotEditorWeekSlots[key] || []);
            return week;
          }, {});
          await this.apiJson(SCHEDULE_TEMPLATE_API, {
            method: 'PUT',
            body: JSON.stringify({ effectiveFrom: this.slotEditorDate, slots: this.slotEditorWeekSlots })
          });
          ElementPlus.ElMessage.success('一周模板已保存。');
        }
        this.slotEditorVisible = false;
        await this.loadScheduleConfig();
      } catch (error) {
        ElementPlus.ElMessage.error(error.message);
      }
    },
    resetDaySlots(day) {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再重置时间格子。');
        return;
      }
      ElementPlus.ElMessageBox.confirm(`重置 ${day.label} 的时间格子？`, '重置当天', {
        confirmButtonText: '重置',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await this.apiJson(`${SCHEDULE_DAY_SLOTS_API}/${day.key}`, { method: 'DELETE' });
          await this.loadScheduleConfig();
          ElementPlus.ElMessage.success('当天已恢复为模板。');
        } catch (error) {
          ElementPlus.ElMessage.error(error.message);
        }
      }).catch(() => {});
    },
    resetAllScheduleConfig() {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再重置时间格子。');
        return;
      }
      ElementPlus.ElMessageBox.confirm('重置全部时间格子设置？所有单日自定义和一周模板都会恢复为系统默认。', '重置全部', {
        confirmButtonText: '重置全部',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await this.apiJson(SCHEDULE_CONFIG_API, { method: 'DELETE' });
          await this.loadScheduleConfig();
          ElementPlus.ElMessage.success('全部时间格子已恢复为默认模板。');
        } catch (error) {
          ElementPlus.ElMessage.error(error.message);
        }
      }).catch(() => {});
    },
    async createTaskOnServer(task) {
      const payload = await this.apiJson(TASKS_API, {
        method: 'POST',
        body: JSON.stringify(task)
      });
      return payload.task;
    },
    async updateTaskOnServer(taskId, task) {
      const payload = await this.apiJson(`${TASKS_API}/${encodeURIComponent(taskId)}`, {
        method: 'PUT',
        body: JSON.stringify(task)
      });
      return payload.task;
    },
    async deleteTaskOnServer(taskId) {
      await this.apiJson(`${TASKS_API}/${encodeURIComponent(taskId)}`, { method: 'DELETE' });
    },
    compareTasks(a, b) {
      const aUnscheduled = !a.dueAt;
      const bUnscheduled = !b.dueAt;
      if (aUnscheduled !== bUnscheduled) return aUnscheduled ? 1 : -1;
      if (aUnscheduled && bUnscheduled) {
        const priorityDiff = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
        if (priorityDiff !== 0) return priorityDiff;
        return a.title.localeCompare(b.title, 'zh-CN');
      }
      const timeDiff = new Date(a.dueAt) - new Date(b.dueAt);
      if (timeDiff !== 0) return timeDiff;
      const priorityDiff = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return a.title.localeCompare(b.title, 'zh-CN');
    },
    startOfDay(date) {
      return new Date(date.getFullYear(), date.getMonth(), date.getDate());
    },
    parseDateKey(dateLike) {
      if (dateLike instanceof Date) return this.startOfDay(dateLike);
      const raw = String(dateLike || '').slice(0, 10);
      const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (!match) return this.startOfDay(new Date());
      return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    },
    timelineStartDate() {
      const today = new Date();
      return this.addDays(this.startOfDay(today), -this.dayRange.past);
    },
    timelineEndDate() {
      return this.addDays(this.startOfDay(new Date()), this.dayRange.future);
    },
    scheduleSyncRange() {
      const today = this.startOfDay(new Date());
      const from = this.formatDateKey(today);
      const timelineEnd = this.timelineEndDate();
      const defaultEnd = this.addDays(today, HABIT_SYNC_FUTURE_DAYS);
      return {
        from,
        to: this.formatDateKey(timelineEnd > defaultEnd ? timelineEnd : defaultEnd)
      };
    },
    ensureDateRangeForKey(dateKey) {
      const target = this.parseDateKey(dateKey);
      const base = this.startOfDay(new Date());
      const offset = this.daysBetween(base, target);
      let changed = false;
      if (offset > this.dayRange.future - DATE_RANGE_EXPAND_MARGIN) {
        this.dayRange.future = offset + DATE_RANGE_EXPAND_MARGIN;
        changed = true;
      }
      if (offset < -this.dayRange.past + DATE_RANGE_EXPAND_MARGIN) {
        this.dayRange.past = Math.abs(offset) + DATE_RANGE_EXPAND_MARGIN;
        changed = true;
      }
      return changed;
    },
    addDays(date, days) {
      const next = new Date(date);
      next.setDate(next.getDate() + days);
      return next;
    },
    weekStartDate(date) {
      const next = this.startOfDay(date);
      const offset = (next.getDay() + 6) % 7;
      next.setDate(next.getDate() - offset);
      return next;
    },
    ddlCalendarWeekStartDate(date) {
      const next = this.startOfDay(date);
      next.setDate(next.getDate() - next.getDay());
      return next;
    },
    daysBetween(baseDate, targetDate) {
      const base = this.startOfDay(baseDate);
      const target = this.startOfDay(targetDate);
      return Math.round((target - base) / 86400000);
    },
    formatDateKey(dateLike) {
      const date = new Date(dateLike);
      return `${date.getFullYear()}-${this.pad(date.getMonth() + 1)}-${this.pad(date.getDate())}`;
    },
    formatDateLabel(dateLike) {
      const date = new Date(dateLike);
      return `${date.getMonth() + 1}/${date.getDate()} ${WEEKDAY_TEXT[date.getDay()]}`;
    },
    formatTime(dateLike) {
      const date = new Date(dateLike);
      return `${this.pad(date.getHours())}:${this.pad(date.getMinutes())}`;
    },
    formatDateTime(dateLike) {
      if (!dateLike) return '—';
      const date = new Date(dateLike);
      if (Number.isNaN(date.getTime())) return String(dateLike);
      return `${date.getFullYear()}-${this.pad(date.getMonth() + 1)}-${this.pad(date.getDate())} ${this.pad(date.getHours())}:${this.pad(date.getMinutes())}`;
    },
    relativeLabel(offset) {
      if (offset === 0) return '今天';
      if (offset === 1) return '明天';
      if (offset === 2) return '后天';
      if (offset === -1) return '昨天';
      if (offset === -2) return '前天';
      if (offset > 0) return `${offset} 天后`;
      return `${Math.abs(offset)} 天前`;
    },
    priorityClass(priority) {
      return `priority-${priority}`;
    },
    priorityLabel(priority) {
      return PRIORITY_LABELS[priority] || '未分类';
    },
    weekdayLabel(key) {
      return WEEKDAY_TEXT[Number(key)] || key;
    },
    habitWeekdaysLabel(habit) {
      const weekdays = Array.isArray(habit.weekdays) ? habit.weekdays : [];
      return weekdays.map(key => this.weekdayLabel(key)).join('、') || '未设置';
    },
    handleHabitSlotChange(keyBase) {
      const slot = this.habitSlotOptions.find(item => item.keyBase === keyBase);
      if (!slot) {
        this.habitForm.slotLabel = '';
        this.habitForm.slotStart = '';
        this.habitForm.slotEnd = '';
        return;
      }
      this.habitForm.slotKeyBase = slot.keyBase;
      this.habitForm.slotLabel = slot.label;
      this.habitForm.slotStart = slot.start;
      this.habitForm.slotEnd = slot.end;
      this.habitForm.durationMinutes = Math.min(Number(this.habitForm.durationMinutes || 30), slot.duration);
    },
    handleHabitStartDateChange() {
      if (!this.habitForm.slotKeyBase) return;
      const slot = this.habitSlotOptions.find(item => item.keyBase === this.habitForm.slotKeyBase);
      if (slot) {
        this.handleHabitSlotChange(slot.keyBase);
        return;
      }
      this.habitForm.slotKeyBase = '';
      this.habitForm.slotLabel = '';
      this.habitForm.slotStart = '';
      this.habitForm.slotEnd = '';
    },
    handleHabitWeekdaysChange() {
      this.handleHabitStartDateChange();
    },
    openHabitDialog(habit = null) {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再新增习惯。');
        return;
      }
      this.habitDialogMode = habit ? 'edit' : 'create';
      this.activeHabitId = habit ? habit.id : '';
      this.habitForm = habit
        ? {
            title: habit.title || '',
            subject: habit.subject || '',
            weekdays: Array.isArray(habit.weekdays) ? [...habit.weekdays] : [],
            slotKeyBase: habit.slotKeyBase || '',
            slotLabel: habit.slotLabel || '',
            slotStart: habit.slotStart || '',
            slotEnd: habit.slotEnd || '',
            durationMinutes: Number(habit.durationMinutes || 30),
            startDate: habit.startDate || this.formatDateKey(new Date()),
            endDate: habit.endDate || '',
            priority: habit.priority || 'medium',
            note: habit.note || '',
            active: habit.active !== false
          }
        : this.emptyHabitForm();
      this.habitDialogVisible = true;
    },
    async saveHabit() {
      if (!this.currentUser) return;
      const title = this.habitForm.title.trim();
      const subject = this.habitForm.subject.trim();
      if (!title || !subject || !this.habitForm.weekdays.length || !this.habitForm.slotKeyBase || !this.habitForm.startDate) {
        ElementPlus.ElMessage.warning('请填写标题、科目、星期、时间格子和开始日期。');
        return;
      }
      const payload = {
        title,
        subject,
        weekdays: this.habitForm.weekdays,
        slotKeyBase: this.habitForm.slotKeyBase,
        slotLabel: this.habitForm.slotLabel,
        slotStart: this.habitForm.slotStart,
        slotEnd: this.habitForm.slotEnd,
        durationMinutes: Number(this.habitForm.durationMinutes || 0),
        startDate: this.habitForm.startDate,
        endDate: this.habitForm.endDate || '',
        priority: this.habitForm.priority,
        note: this.habitForm.note.trim(),
        active: !!this.habitForm.active
      };
      try {
        if (this.habitDialogMode === 'edit') {
          await this.apiJson(`${HABITS_API}/${encodeURIComponent(this.activeHabitId)}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
          });
          ElementPlus.ElMessage.success('习惯已更新。');
        } else {
          await this.apiJson(HABITS_API, {
            method: 'POST',
            body: JSON.stringify(payload)
          });
          ElementPlus.ElMessage.success('习惯已创建。');
        }
        this.habitDialogVisible = false;
        await this.loadHabits();
        await this.loadTasks();
        await this.loadScheduleItems();
      } catch (error) {
        ElementPlus.ElMessage.error(`保存习惯失败：${error.message}`);
      }
    },
    deleteHabit(habit) {
      if (!habit || !this.currentUser) return;
      ElementPlus.ElMessageBox.confirm(
        `删除习惯「${habit.title}」？今天及未来的相关安排会一起删除，过去记录保留。`,
        '删除习惯',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        try {
          await this.apiJson(`${HABITS_API}/${encodeURIComponent(habit.id)}`, { method: 'DELETE' });
          ElementPlus.ElMessage.success('习惯已删除。');
          if (this.activeHabitId === habit.id) {
            this.habitDialogVisible = false;
            this.activeHabitId = '';
          }
          await this.loadHabits();
          await this.loadScheduleItems();
        } catch (error) {
          ElementPlus.ElMessage.error(`删除习惯失败：${error.message}`);
        }
      }).catch(() => {});
    },
    ddlTasksForDate(key) {
      return this.todoTasksByDueDate[key] || [];
    },
    setDdlViewMode(mode) {
      if (mode === this.ddlViewMode) return;
      if (this.activePage === 'ddl') this.rememberCurrentViewDate('ddl');
      this.ddlViewMode = mode;
      const key = this.pageViewDateKeys.ddl || this.currentViewDateKey || this.formatDateKey(new Date());
      this.setDdlCalendarMonth(key);
      if (mode === 'timeline') {
        this.$nextTick(() => this.scrollToDate(key, 'ddl', 'instant'));
      }
    },
    setDdlCalendarMonth(dateLike) {
      const date = this.parseDateKey(dateLike);
      this.ddlCalendarMonthKey = this.formatDateKey(new Date(date.getFullYear(), date.getMonth(), 1));
    },
    shiftDdlCalendarMonth(offset) {
      const base = this.parseDateKey(this.ddlCalendarMonthKey || this.currentViewDateKey || this.formatDateKey(new Date()));
      const target = new Date(base.getFullYear(), base.getMonth() + offset, 1);
      this.setDdlCalendarMonth(target);
      const selected = this.formatDateKey(target);
      this.currentViewDateKey = selected;
      this.pageViewDateKeys.ddl = selected;
    },
    goToDdlCalendarToday() {
      this.scrollToDate(new Date(), 'ddl');
    },
    jumpDdlCalendarDayToTimeline(dateLike) {
      const targetDate = this.parseDateKey(dateLike);
      const key = this.formatDateKey(targetDate);
      this.currentViewDateKey = key;
      this.pageViewDateKeys.ddl = key;
      this.pauseTimelineAutoExpand();
      this.ddlViewMode = 'timeline';
      this.$nextTick(() => {
        window.requestAnimationFrame(() => this.scrollToDate(targetDate, 'ddl', 'smooth'));
      });
    },
    openDdlCalendarTask(task) {
      if (this.adminMode) return;
      this.openEditDialog(task);
    },
    openCreateDialog() {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再新增。');
        return;
      }
      if (this.activePage === 'daily') {
        this.openDirectScheduleCreateDialog();
        return;
      }
      this.dialogMode = 'create';
      this.createDialogType = 'task';
      this.activeTaskId = null;
      this.activeTaskPool = 'todo';
      this.form = this.emptyForm();
      this.dialogVisible = true;
    },
    openPoolTaskCreateDialog() {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再新增临时任务池任务。');
        return;
      }
      this.dialogMode = 'create';
      this.createDialogType = 'arrangement';
      this.activeTaskId = null;
      this.activeTaskPool = 'arrangement';
      this.form = this.emptyForm();
      this.form.unscheduled = true;
      this.form.date = '';
      this.form.time = '';
      this.dialogVisible = true;
    },
    openEditDialog(task) {
      if (this.adminMode) return;
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再编辑任务。');
        return;
      }
      this.dialogMode = 'edit';
      this.createDialogType = 'task';
      this.activeTaskId = task.id;
      this.activeTaskPool = this.taskPool(task);
      const due = task.dueAt ? new Date(task.dueAt) : new Date();
      this.form = {
        title: task.title,
        subject: task.subject || '',
        date: task.dueAt ? this.formatDateKey(due) : this.formatDateKey(new Date()),
        time: task.dueAt ? this.formatTime(due) : '23:59',
        unscheduled: this.taskPool(task) === 'arrangement' || !task.dueAt,
        priority: task.priority,
        note: task.note || '',
        completed: !!task.completed
      };
      this.dialogVisible = true;
    },
    buildDueAt() {
      // Empty dueAt means the task stays in the unscheduled/flexible pool.
      if (this.isArrangementDialog) return '';
      if (this.form.unscheduled) return '';
      if (!this.form.date || !this.form.time) return null;
      const normalizedTime = this.normalizeTimeText(this.form.time);
      if (!normalizedTime) return null;
      this.form.time = normalizedTime;
      return `${this.form.date}T${normalizedTime}:00`;
    },
    async saveTask() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再保存任务。');
        return;
      }
      if (this.isArrangementDialog) {
        this.form.unscheduled = true;
        this.form.date = '';
        this.form.time = '';
      }
      const title = this.form.title.trim();
      const subject = this.form.subject.trim();
      const dueAt = this.buildDueAt();
      if (!title || !subject || dueAt === null) {
        ElementPlus.ElMessage.warning('请先填写标题、科目；如果要设置截止时间，也要填日期和 H:mm 或 HH:mm 格式的时间。');
        return;
      }
      if (subject.length > 40) {
        ElementPlus.ElMessage.warning('科目不能超过 40 个字符。');
        return;
      }

      const payload = {
        title,
        subject,
        dueAt,
        pool: this.isArrangementDialog ? 'arrangement' : 'todo',
        priority: this.form.priority,
        note: this.form.note.trim(),
        completed: !!this.form.completed
      };
      if (this.isArrangementDialog) payload.dueAt = '';

      try {
        if (this.dialogMode === 'create') {
          const task = { id: this.createTaskId(), createdAt: new Date().toISOString(), ...payload };
          const savedTask = await this.createTaskOnServer(task);
          this.tasks = [...this.tasks, savedTask || task];
          ElementPlus.ElMessage.success('任务已创建。');
        } else {
          const existing = this.tasks.find(task => task.id === this.activeTaskId);
          if (!existing) return;
          const nextTask = { ...existing, ...payload, updatedAt: new Date().toISOString() };
          const savedTask = await this.updateTaskOnServer(this.activeTaskId, nextTask);
          this.tasks = this.tasks.map(task => task.id === this.activeTaskId ? (savedTask || nextTask) : task);
          await this.loadScheduleItems();
          ElementPlus.ElMessage.success('任务已更新。');
        }
        this.dialogVisible = false;
        if (payload.dueAt) this.$nextTick(() => this.scrollToDate(payload.dueAt, this.activePage, 'instant'));
      } catch (error) {
        console.error('保存任务失败：', error);
        ElementPlus.ElMessage.error(`保存失败：${error.message}`);
      }
    },
    async toggleComplete(taskId) {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再修改任务。');
        return;
      }
      const task = this.tasks.find(item => item.id === taskId);
      if (!task) return;
      const nextCompleted = !task.completed;
      const nextTask = { ...task, completed: nextCompleted, updatedAt: new Date().toISOString() };
      try {
        const savedTask = await this.updateTaskOnServer(taskId, nextTask);
        this.tasks = this.tasks.map(item => item.id === taskId ? (savedTask || nextTask) : item);
        await this.loadScheduleItems();
        this.form.completed = nextCompleted;
        this.dialogVisible = false;
        ElementPlus.ElMessage.success(nextCompleted ? '已标记完成。' : '已取消完成。');
      } catch (error) {
        console.error('修改任务状态失败：', error);
        ElementPlus.ElMessage.error(`修改失败：${error.message}`);
      }
    },
    deleteTask(taskId) {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再删除任务。');
        return;
      }
      ElementPlus.ElMessageBox.confirm('删除后将无法恢复，确定继续吗？', '删除任务', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await this.deleteTaskOnServer(taskId);
          this.tasks = this.tasks.filter(task => task.id !== taskId);
          this.scheduleItems = this.scheduleItems.filter(item => item.taskId !== taskId);
          this.dialogVisible = false;
          ElementPlus.ElMessage.success('任务已删除。');
        } catch (error) {
          console.error('删除任务失败：', error);
          ElementPlus.ElMessage.error(`删除失败：${error.message}`);
        }
      }).catch(() => {});
    },
    scrollToToday() {
      this.scrollToDate(this.startOfDay(new Date()));
    },
    scrollSidebarToToday() {
      this.scrollToDate(this.startOfDay(new Date()), this.activePage, 'smooth', 'peek-start');
    },
    handleQuickJumpDateChange(value) {
      if (!value) return;
      this.scrollToDate(value);
    },
    quickJumpDateCellClassName(date) {
      if (!date) return '';
      const parsedDate = new Date(date);
      if (Number.isNaN(parsedDate.getTime())) return '';
      return this.quickJumpMarkedDateKeys.has(this.formatDateKey(parsedDate))
        ? 'has-quick-jump-task'
        : '';
    },
    switchPage(page) {
      if (page === this.activePage) return;
      this.rememberCurrentViewDate(this.activePage);
      this.activePage = page;
      const key = this.pageViewDateKeys[page] || this.currentViewDateKey || this.formatDateKey(new Date());
      this.$nextTick(() => {
        if (page === 'ddl') this.setDdlCalendarMonth(key);
        this.scrollToDate(key, page, 'instant');
        if (this.guideVisible && this.currentGuideStep && this.currentGuideStep.waitForPage === page) {
          window.setTimeout(() => this.nextGuideStep(), 120);
        }
      });
    },
    scrollToDate(dateLike, page = this.activePage, behavior = 'smooth', align = 'center') {
      const targetDate = this.parseDateKey(dateLike);
      const key = this.formatDateKey(targetDate);
      const expanded = this.ensureDateRangeForKey(key);
      if (expanded) {
        if (this.currentUser && (page === 'daily' || this.activePage === 'daily')) {
          this.loadScheduleItems();
        }
        this.$nextTick(() => this.scrollToDate(targetDate, page, behavior, align));
        return;
      }
      if (page === 'ddl' && this.ddlViewMode === 'calendar') {
        this.currentViewDateKey = key;
        this.pageViewDateKeys.ddl = key;
        this.setDdlCalendarMonth(targetDate);
        return;
      }
      const container = page === 'daily' ? this.$refs.dailyScroll : this.$refs.timelineScroll;
      if (!container) return;
      const target = container.querySelector(`[data-day="${key}"]`);
      if (!target) return;
      const maxScrollLeft = Math.max(0, container.scrollWidth - container.clientWidth);
      const containerRect = container.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const targetLeft = container.scrollLeft + targetRect.left - containerRect.left;
      const targetCenter = targetLeft + targetRect.width / 2;
      const viewportCenter = container.clientWidth / 2;
      const peekOffset = align === 'peek-start' ? 24 : 0;
      const rawLeft = align === 'start' || align === 'peek-start'
        ? targetLeft - peekOffset
        : targetCenter - viewportCenter;
      const nextLeft = Math.min(maxScrollLeft, Math.max(0, rawLeft));
      this.currentViewDateKey = key;
      this.pageViewDateKeys[page] = key;
      this.pauseTimelineAutoExpand(behavior === 'smooth' ? 700 : 120);
      if (behavior === 'instant') {
        const previousBehavior = container.style.scrollBehavior;
        container.style.scrollBehavior = 'auto';
        container.scrollLeft = nextLeft;
        container.style.scrollBehavior = previousBehavior;
        return;
      }
      container.scrollTo({ left: nextLeft, behavior });
    },
    rememberCurrentViewDate(page) {
      if (page === 'ddl' && this.ddlViewMode === 'calendar') {
        const key = this.pageViewDateKeys.ddl || this.currentViewDateKey || this.formatDateKey(new Date());
        this.pageViewDateKeys.ddl = key;
        this.currentViewDateKey = key;
        this.setDdlCalendarMonth(key);
        return;
      }
      const container = page === 'daily' ? this.$refs.dailyScroll : this.$refs.timelineScroll;
      if (!container) return;
      const columns = [...container.querySelectorAll('[data-day]')];
      if (!columns.length) return;
      const viewportCenter = container.scrollLeft + container.clientWidth / 2;
      const containerRect = container.getBoundingClientRect();
      const nearest = columns.reduce((best, column) => {
        const columnRect = column.getBoundingClientRect();
        const center = container.scrollLeft + columnRect.left - containerRect.left + columnRect.width / 2;
        const distance = Math.abs(center - viewportCenter);
        return distance < best.distance ? { column, distance } : best;
      }, { column: columns[0], distance: Number.POSITIVE_INFINITY }).column;
      const key = nearest.dataset.day;
      if (!key) return;
      this.pageViewDateKeys[page] = key;
      if (page === this.activePage) this.currentViewDateKey = key;
    },
    handleTimelineScroll(page) {
      const container = page === 'daily' ? this.$refs.dailyScroll : this.$refs.timelineScroll;
      if (!container) return;
      if (this.suppressTimelineAutoExpand) return;
      let expanded = false;
      if (container.scrollLeft + container.clientWidth > container.scrollWidth - 320) {
        this.dayRange.future += 30;
        expanded = true;
      }
      if (container.scrollLeft < 240) {
        this.dayRange.past += 30;
        expanded = true;
      }
      if (expanded && this.currentUser && page === 'daily') {
        this.loadScheduleItems();
      }
    },
    pauseTimelineAutoExpand(duration = 500) {
      this.suppressTimelineAutoExpand = true;
      if (this.timelineAutoExpandTimer) window.clearTimeout(this.timelineAutoExpandTimer);
      this.timelineAutoExpandTimer = window.setTimeout(() => {
        this.suppressTimelineAutoExpand = false;
        this.timelineAutoExpandTimer = null;
      }, duration);
    },
    jumpToOffset(days) {
      const base = this.parseDateKey(this.currentViewDateKey);
      const target = this.addDays(base, days);
      this.scrollToDate(target);
    },
    pad(value) {
      return String(value).padStart(2, '0');
    },
    createTaskId() {
      if (window.crypto && typeof window.crypto.randomUUID === 'function') {
        return window.crypto.randomUUID();
      }
      return `task-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    },
    createSlotKeyBase() {
      return `custom-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
  }
}).use(ElementPlus).mount('#app');
