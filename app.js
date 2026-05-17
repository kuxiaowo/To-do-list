const { createApp } = Vue;
const LEGACY_STORAGE_KEY = 'todo-list-timeline-v1';
const LEGACY_MIGRATION_KEY = 'todo-list-timeline-migrated-v1';
const TASKS_API = '/api/tasks';
const TASKS_BULK_API = '/api/tasks/bulk';
const AUTH_API = '/api/auth';
const SCHEDULE_API = '/api/schedule-items';
const AUTH_TOKEN_KEY = 'todo-list-auth-token-v1';
const THEME_STORAGE_KEY = 'todo-list-theme-v1';
const TIMELINE_START_MONTH = 4;
const TIMELINE_START_DAY = 1;
const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 };
const PRIORITY_LABELS = { high: '高优先级', medium: '中优先级', low: '低优先级' };
const WEEKDAY_TEXT = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
const SCHEDULE_TEMPLATES = {
  weekday: [
    { label: '午休', start: '13:00', end: '13:45' },
    { label: '晚饭后', start: '18:00', end: '18:40' },
    { label: '第一节晚自习', start: '18:40', end: '19:40' },
    { label: '第二节晚自习', start: '19:50', end: '20:40' },
    { label: '第三节晚自习', start: '20:50', end: '21:30' },
  ],
  friday: [
    { label: '午休', start: '13:00', end: '13:45' },
  ],
  weekend: [
    { label: '上午', start: '09:00', end: '10:00' },
    { label: '上午', start: '10:00', end: '11:00' },
    { label: '上午', start: '11:00', end: '12:00' },
    { label: '下午', start: '14:00', end: '15:00' },
    { label: '下午', start: '15:00', end: '16:00' },
    { label: '下午', start: '17:00', end: '18:00' },
    { label: '晚上', start: '19:00', end: '20:00' },
  ],
};

createApp({
  data() {
    return {
      tasks: [],
      scheduleItems: [],
      showCompleted: false,
      isDarkMode: (localStorage.getItem(THEME_STORAGE_KEY) || 'light') === 'dark',
      activePage: 'ddl',
      pageViewDateKeys: { ddl: '', daily: '' },
      dialogVisible: false,
      dialogMode: 'create',
      activeTaskId: null,
      currentViewDateKey: '',
      form: this.emptyForm(),
      dayRange: { past: 90, future: 90 },
      authToken: localStorage.getItem(AUTH_TOKEN_KEY) || '',
      currentUser: null,
      authMode: 'login',
      accountMenuOpen: false,
      draggedTaskId: null,
      scheduleDialogVisible: false,
      scheduleDialogMode: 'create',
      activeScheduleItemId: null,
      activeScheduleTask: null,
      activeScheduleSlot: null,
      scheduleForm: { durationMinutes: 30, note: '', completed: false },
      loginForm: { nickname: '', password: '' },
      registerForm: { name: '', nickname: '', password: '' }
    };
  },
  computed: {
    sortedTasks() {
      return [...this.tasks].sort((a, b) => this.compareTasks(a, b));
    },
    filteredTasks() {
      return this.sortedTasks.filter(task => this.showCompleted || !task.completed);
    },
    unscheduledTasks() {
      return this.filteredTasks
        .filter(task => !task.dueAt)
        .sort((a, b) => this.compareTasks(a, b));
    },
    unscheduledCount() {
      return this.unscheduledTasks.length;
    },
    unscheduledByPriority() {
      return ['high', 'medium', 'low'].map(priority => ({
        key: priority,
        label: PRIORITY_LABELS[priority],
        tasks: this.unscheduledTasks.filter(task => task.priority === priority)
      }));
    },
    dayColumns() {
      const base = this.startOfDay(new Date());
      const start = this.timelineStartDate();
      const end = this.addDays(base, this.dayRange.future);
      const days = [];
      for (let date = new Date(start); date <= end; date = this.addDays(date, 1)) {
        const offset = this.daysBetween(base, date);
        const key = this.formatDateKey(date);
        const tasks = this.filteredTasks.filter(task => task.dueAt && task.dueAt.startsWith(key));
        days.push({
          key,
          label: this.formatDateLabel(date),
          subtitle: this.relativeLabel(offset),
          tasks
        });
      }
      return days;
    },
    avatarText() {
      if (!this.currentUser) return '登';
      const source = this.currentUser.nickname || this.currentUser.name || '?';
      return source.trim().slice(0, 1).toUpperCase();
    },
    ddlTasks() {
      return this.sortedTasks.filter(task => task.dueAt && !task.completed);
    },
    scheduleItemsBySlot() {
      return this.scheduleItems.reduce((groups, item) => {
        const key = this.scheduleSlotKey(item.date, item.slotKey);
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
        return groups;
      }, {});
    },
    scheduleDayColumns() {
      const base = this.startOfDay(new Date());
      const start = this.timelineStartDate();
      const end = this.addDays(base, 21);
      const days = [];
      for (let date = new Date(start); date <= end; date = this.addDays(date, 1)) {
        const offset = this.daysBetween(base, date);
        const key = this.formatDateKey(date);
        const weekday = date.getDay();
        const templateKey = weekday >= 1 && weekday <= 4 ? 'weekday' : weekday === 5 ? 'friday' : 'weekend';
        days.push({
          key,
          label: this.formatDateLabel(date),
          subtitle: this.relativeLabel(offset),
          slots: SCHEDULE_TEMPLATES[templateKey].map((slot, index) => ({
            ...slot,
            key: `${key}-${index}-${slot.start}`,
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
    document.addEventListener('click', this.closeAccountMenu);
    await this.loadCurrentUser();
    await this.loadTasks();
    await this.loadScheduleItems();
    this.$nextTick(() => this.scrollToDate(this.currentViewDateKey, 'ddl', 'auto'));
  },
  beforeUnmount() {
    document.removeEventListener('click', this.closeAccountMenu);
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
    getLegacyTasks() {
      const raw = localStorage.getItem(LEGACY_STORAGE_KEY);
      if (!raw) return [];
      try {
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : [];
      } catch (error) {
        console.error('读取旧 localStorage 失败：', error);
        return [];
      }
    },
    authHeaders() {
      return this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {};
    },
    async apiJson(url, options = {}) {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...(options.body ? { 'Content-Type': 'application/json' } : {}),
          ...this.authHeaders(),
          ...(options.headers || {})
        }
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || '请求失败');
      return payload;
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
        await this.loadTasks();
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
        await this.loadTasks();
        await this.loadScheduleItems();
        ElementPlus.ElMessage.success('注册成功，已自动登录。');
      } catch (error) {
        ElementPlus.ElMessage.error(`注册失败：${error.message}`);
      }
    },
    async logout() {
      if (this.authToken) {
        await this.apiJson(`${AUTH_API}/logout`, { method: 'POST' }).catch(() => {});
      }
      this.authToken = '';
      this.currentUser = null;
      this.tasks = [];
      this.scheduleItems = [];
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
        const serverTasks = Array.isArray(payload.tasks) ? payload.tasks : [];
        if (serverTasks.length === 0 && localStorage.getItem(LEGACY_MIGRATION_KEY) !== 'done') {
          const legacyTasks = this.getLegacyTasks();
          if (legacyTasks.length) {
            this.tasks = legacyTasks;
            await this.persistTasks();
            localStorage.setItem(LEGACY_MIGRATION_KEY, 'done');
            ElementPlus.ElMessage.success('已把旧浏览器本地任务迁移到服务器。');
            return;
          }
        }
        this.tasks = serverTasks;
      } catch (error) {
        console.error('读取服务器任务失败：', error);
        this.tasks = this.getLegacyTasks();
        if (this.tasks.length) {
          ElementPlus.ElMessage.warning('服务器暂时不可用，先加载了浏览器本地旧数据。');
        } else {
          ElementPlus.ElMessage.error('任务数据读取失败，请检查服务是否正常运行。');
        }
      }
    },
    async loadScheduleItems() {
      if (!this.currentUser) {
        this.scheduleItems = [];
        return;
      }
      try {
        const payload = await this.apiJson(SCHEDULE_API, { cache: 'no-store' });
        this.scheduleItems = Array.isArray(payload.items) ? payload.items : [];
      } catch (error) {
        console.error('读取每日安排失败：', error);
        ElementPlus.ElMessage.error('每日安排读取失败。');
      }
    },
    minutesBetween(start, end) {
      const [sh, sm] = start.split(':').map(Number);
      const [eh, em] = end.split(':').map(Number);
      return (eh * 60 + em) - (sh * 60 + sm);
    },
    scheduleItemsForSlot(date, slotKey) {
      return this.scheduleItemsBySlot[this.scheduleSlotKey(date, slotKey)] || [];
    },
    slotUsedMinutes(date, slotKey, excludeId = null) {
      return this.scheduleItemsForSlot(date, slotKey)
        .filter(item => item.id !== excludeId)
        .reduce((sum, item) => sum + Number(item.durationMinutes || 0), 0);
    },
    scheduleSlotKey(date, slotKey) {
      return `${date}::${slotKey}`;
    },
    handleDropOnSlot(day, slot) {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再创建安排。');
        return;
      }
      const task = this.tasks.find(item => item.id === this.draggedTaskId);
      if (!task) return;
      this.scheduleDialogMode = 'create';
      this.activeScheduleItemId = null;
      this.activeScheduleTask = task;
      this.activeScheduleSlot = { ...slot, date: day.key, dateLabel: day.label };
      const remaining = Math.max(1, slot.duration - this.slotUsedMinutes(day.key, slot.key));
      this.scheduleForm = { durationMinutes: Math.min(30, remaining), note: '', completed: false };
      this.scheduleDialogVisible = true;
      this.draggedTaskId = null;
    },
    openScheduleEditDialog(item) {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再编辑安排。');
        return;
      }
      const task = this.tasks.find(taskItem => taskItem.id === item.taskId) || item.task;
      this.scheduleDialogMode = 'edit';
      this.activeScheduleItemId = item.id;
      this.activeScheduleTask = task;
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
        durationMinutes: Number(item.durationMinutes || 1),
        note: item.note || '',
        completed: !!item.completed
      };
      this.scheduleDialogVisible = true;
    },
    async saveScheduleItem() {
      if (!this.currentUser || !this.activeScheduleTask || !this.activeScheduleSlot) return;
      const used = this.slotUsedMinutes(
        this.activeScheduleSlot.date,
        this.activeScheduleSlot.key,
        this.scheduleDialogMode === 'edit' ? this.activeScheduleItemId : null
      );
      const duration = Number(this.scheduleForm.durationMinutes || 0);
      if (used + duration > this.activeScheduleSlot.duration) {
        ElementPlus.ElMessage.error(`时间段容量不足：已用 ${used} 分钟，总共 ${this.activeScheduleSlot.duration} 分钟。`);
        return;
      }
      const payload = {
        taskId: this.activeScheduleTask.id,
        date: this.activeScheduleSlot.date,
        slotKey: this.activeScheduleSlot.key,
        slotLabel: this.activeScheduleSlot.label,
        slotStart: this.activeScheduleSlot.start,
        slotEnd: this.activeScheduleSlot.end,
        durationMinutes: duration,
        note: this.scheduleForm.note.trim(),
        completed: !!this.scheduleForm.completed
      };
      try {
        if (this.scheduleDialogMode === 'create') {
          await this.apiJson(SCHEDULE_API, { method: 'POST', body: JSON.stringify(payload) });
          ElementPlus.ElMessage.success('安排已创建。');
        } else {
          await this.apiJson(`${SCHEDULE_API}/${this.activeScheduleItemId}`, { method: 'PUT', body: JSON.stringify(payload) });
          ElementPlus.ElMessage.success('安排已更新。');
        }
        this.scheduleDialogVisible = false;
        await this.loadScheduleItems();
      } catch (error) {
        ElementPlus.ElMessage.error(`保存失败：${error.message}`);
      }
    },
    async toggleScheduleComplete() {
      this.scheduleForm.completed = !this.scheduleForm.completed;
      await this.saveScheduleItem();
    },
    deleteScheduleItem() {
      if (!this.activeScheduleItemId) return;
      ElementPlus.ElMessageBox.confirm('删除这个安排？不会删除原 DDL。', '删除安排', {
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
    async persistTasks() {
      if (!this.currentUser) throw new Error('请先登录后再保存');
      const response = await fetch(TASKS_BULK_API, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
        body: JSON.stringify({ tasks: this.tasks })
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || '服务器保存失败');
      }
      localStorage.setItem(LEGACY_MIGRATION_KEY, 'done');
    },
    async createTaskOnServer(task) {
      const payload = await this.apiJson(TASKS_API, {
        method: 'POST',
        body: JSON.stringify(task)
      });
      localStorage.setItem(LEGACY_MIGRATION_KEY, 'done');
      return payload.task;
    },
    async updateTaskOnServer(taskId, task) {
      const payload = await this.apiJson(`${TASKS_API}/${encodeURIComponent(taskId)}`, {
        method: 'PUT',
        body: JSON.stringify(task)
      });
      localStorage.setItem(LEGACY_MIGRATION_KEY, 'done');
      return payload.task;
    },
    async deleteTaskOnServer(taskId) {
      await this.apiJson(`${TASKS_API}/${encodeURIComponent(taskId)}`, { method: 'DELETE' });
      localStorage.setItem(LEGACY_MIGRATION_KEY, 'done');
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
    timelineStartDate() {
      const today = new Date();
      return new Date(today.getFullYear(), TIMELINE_START_MONTH, TIMELINE_START_DAY);
    },
    addDays(date, days) {
      const next = new Date(date);
      next.setDate(next.getDate() + days);
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
    openCreateDialog() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再新增任务。');
        return;
      }
      this.dialogMode = 'create';
      this.activeTaskId = null;
      this.form = this.emptyForm();
      this.dialogVisible = true;
    },
    openEditDialog(task) {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再编辑任务。');
        return;
      }
      this.dialogMode = 'edit';
      this.activeTaskId = task.id;
      const due = task.dueAt ? new Date(task.dueAt) : new Date();
      this.form = {
        title: task.title,
        subject: task.subject || '',
        date: task.dueAt ? this.formatDateKey(due) : this.formatDateKey(new Date()),
        time: task.dueAt ? this.formatTime(due) : '23:59',
        unscheduled: !task.dueAt,
        priority: task.priority,
        note: task.note || '',
        completed: !!task.completed
      };
      this.dialogVisible = true;
    },
    buildDueAt() {
      if (this.form.unscheduled) return '';
      if (!this.form.date || !this.form.time) return null;
      return `${this.form.date}T${this.form.time}:00`;
    },
    async saveTask() {
      if (!this.currentUser) {
        ElementPlus.ElMessage.warning('请先登录或注册，再保存任务。');
        return;
      }
      const title = this.form.title.trim();
      const subject = this.form.subject.trim();
      const dueAt = this.buildDueAt();
      if (!title || !subject || dueAt === null) {
        ElementPlus.ElMessage.warning('请先填写标题、科目；如果要设置截止时间，也要填日期和时间。');
        return;
      }

      const payload = {
        title,
        subject,
        dueAt,
        priority: this.form.priority,
        note: this.form.note.trim(),
        completed: !!this.form.completed
      };

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
        if (payload.dueAt) this.$nextTick(() => this.scrollToDate(payload.dueAt));
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
    switchPage(page) {
      if (page === this.activePage) return;
      this.rememberCurrentViewDate(this.activePage);
      this.activePage = page;
      const key = this.pageViewDateKeys[page] || this.currentViewDateKey || this.formatDateKey(new Date());
      this.$nextTick(() => this.scrollToDate(key, page, 'auto'));
    },
    scrollToDate(dateLike, page = this.activePage, behavior = 'smooth') {
      const key = this.formatDateKey(dateLike);
      const container = page === 'daily' ? this.$refs.dailyScroll : this.$refs.timelineScroll;
      if (!container) return;
      const target = container.querySelector(`[data-day="${key}"]`);
      if (!target) return;
      const maxScrollLeft = Math.max(0, container.scrollWidth - container.clientWidth);
      const targetCenter = target.offsetLeft + target.offsetWidth / 2;
      const viewportCenter = container.clientWidth / 2;
      const nextLeft = Math.min(maxScrollLeft, Math.max(0, targetCenter - viewportCenter));
      this.currentViewDateKey = key;
      this.pageViewDateKeys[page] = key;
      container.scrollTo({ left: nextLeft, behavior });
    },
    rememberCurrentViewDate(page) {
      const container = page === 'daily' ? this.$refs.dailyScroll : this.$refs.timelineScroll;
      if (!container) return;
      const columns = [...container.querySelectorAll('[data-day]')];
      if (!columns.length) return;
      const viewportCenter = container.scrollLeft + container.clientWidth / 2;
      const nearest = columns.reduce((best, column) => {
        const center = column.offsetLeft + column.offsetWidth / 2;
        const distance = Math.abs(center - viewportCenter);
        return distance < best.distance ? { column, distance } : best;
      }, { column: columns[0], distance: Number.POSITIVE_INFINITY }).column;
      const key = nearest.dataset.day;
      if (!key) return;
      this.pageViewDateKeys[page] = key;
      if (page === this.activePage) this.currentViewDateKey = key;
    },
    jumpToOffset(days) {
      const base = new Date(`${this.currentViewDateKey}T00:00:00`);
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
    }
  }
}).use(ElementPlus).mount('#app');
