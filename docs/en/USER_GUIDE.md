# User Guide

[中文](../zh-CN/USER_GUIDE.md) | [English](./USER_GUIDE.md)

This document is intended for ordinary users and administrators of To-Do List Timeline, explaining the main functions, usage paths, and limitations of the page. The interface details will not be expanded here. If you need a developer interface description, please see [API.md](./API.md).

## Quick start

1. Open the application homepage, such as `http://localhost:8092`.
2. Click the account entry in the upper right corner.
3. Register an account or log in using an existing account.
4. Add a task with a deadline in the "DDL Date Timeline", or switch to "Daily Schedule" and drag the task into the specific time grid.

The page can be opened when not logged in, but data such as tasks, daily schedules, feedback, etc. will not be saved; you need to log in or register first.

## Account

### Register and log in

- Registration requires filling in name, nickname and password.
- Nickname is used for login. The same nickname cannot be reused by multiple accounts.
- Password must be at least 6 characters long.
- You will automatically log in after successful registration.

### Account menu

After logging in, the current account will be displayed in the account entry in the upper right corner. Ordinary users can:

- Modify nickname: Nickname cannot be empty, can be up to 32 characters, and cannot be repeated with other users.
- Change password: You need to enter the original password, new password and confirmation password; the new password must be at least 6 digits.
- Log out: After logging out, the user data in the current page will be cleared and returned to the non-logged-in state.

Administrator accounts can also open the Admin panel from the account menu.

## Beginner’s Guide

When you enter the normal to-do page for the first time, the system will display the newbie guide. The guidance will explain:

- Log in to your account first.
- Where to add tasks from.
- The role of the task pool on the left.
- The difference between "DDL Date Timeline" and "Daily Schedule".
- How to drag DDL into the daily time grid.
- How to submit feedback.

You can click "Skip" to end the guide. When switching to a tab that requires operation, the guidance will ask you to click the corresponding tab before continuing. No beating around the bush here: if you’re already familiar with the page, it’s perfectly okay to skip it.

## DDL Date Timeline

"DDL Date Timeline" is used to view and manage tasks with deadlines.

### Add new task

Click "Add Task" and fill in:

- Title: task name, cannot be empty.
- Subject: Can be selected from the drop-down list or entered directly.
- Time arrangement: You can set the deadline, or you can put it in "to be arranged" first.
- Deadline date and deadline: Only required when "Set deadline" is selected.
- Priority: high, medium, low, corresponding to red, yellow, green marks.
- Notes: Used to record page numbers, question numbers, locations, materials or other instructions.

After saving:

- Tasks with deadlines will automatically appear in the corresponding date column.
- Tasks with no deadline will remain in "To be scheduled" on the left.
- Tasks are sorted by deadline, priority, and title.

### View and locate

- The page displays tasks horizontally by date.
- You can click "Locate Today" to return to today.
- You can use date jump to quickly locate a certain day.
- You can move the timeline view using shortcuts such as "Next week".
- You can turn on "Show Completed" to view completed tasks; completed tasks will be hidden when turned off.

### Edit, Complete and Delete

Click the task card to open the task details. Details can be found in:

- Modify title, account, deadline, priority and notes.
- Mark completion or cancel completion.
- Delete the task.

There are two linkage rules that need to be noted:

- When an unfinished DDL task is marked completed, all unfinished Daily Schedules associated with the task will also be marked completed simultaneously.
- When a completed DDL task is canceled, the completed daily schedule will not be automatically canceled and needs to be processed separately in the corresponding schedule.
- Deleting a task will also delete all daily schedules associated with it; deleting a schedule will not delete the original task.

## Daily schedule

"Daily Schedule" is used to split tasks into specific dates and time periods for execution.

### Unscheduled tasks

The "To Be Arranged" on the left displays tasks that have not yet been determined to have a deadline or that need to be arranged flexibly. After switching to "Daily Schedule", you can:

- Click "Add" in the column to create a to-be-scheduled task with no deadline.
- Drag the scheduled task to any date and set the start time and duration.
- Click on the task card to add the deadline or modify the task details.

Tasks in the old version of the elastic task pool will continue to be displayed here, and there is no need to migrate data.

### Bottom DDL list

There is "DDL by Time" at the bottom of the daily schedule. DDL tasks with deadlines that have not yet been completed are displayed here.

You can do two things with DDL:

- Drag to a time grid above to create a daily schedule.
- Click directly on the DDL card to open task details, modify or mark completed.

The same DDL can be repeatedly dragged to different time grids to split it into multiple learning arrangements.

### Create a schedule

After dragging the to-be-scheduled task or bottom DDL to a certain day, the "Create Daily Schedule" window will open. Need to confirm:

- Schedule task: from the dragged task.
- Time period: from the target time grid.
- Estimated duration: By default, it does not exceed the remaining capacity of the current grid.
- Note: Record the specific goals of this arrangement, such as page number, question number or review scope.

After saving, the schedule card will appear in the time grid.

### Edit, move and finalize arrangements

Click on the schedule card to open Schedule Details/Edit. Can:

- Modifies the estimated duration.
- Modify comments.
- Mark completion or cancel completion.
- Delete an arrangement.

You can also drag existing arrangements to other time grids, or drag them to different positions in the same grid to adjust the order. The new date, time period and sorting will be saved after adjustment.

Completing a schedule item affects only that item and does not automatically complete the original DDL task. Conversely, when a DDL task changes from incomplete to completed, its linked unfinished schedule items are also marked completed.

Completed arrangements will not continue to participate in time conflict calculations; even if completed arrangements are currently hidden, other arrangements will not have invisible conflict objects.

## Time grid

Daily schedule depends on time grid. Each grid has a name, start time and end time, for example "18:00-18:40 after dinner".

### Weekly template

Click "Edit Weekly Template" to maintain the default time grid for each day of the week.

- The template is effective starting from the currently selected date.
- Future dates that are not individually customized will use the corresponding week template.
- The time format will be verified before saving, supporting `H:mm` or `HH:mm`, such as `9:00`, `18:40`.
- The end time must be later than the start time.

### Single day time grid

Click the edit entry on a certain day to modify only the time grid for that day.

- Single day settings only affect this day.
- Single day settings have priority over weekly templates.
- You can add or delete time periods for the current day.
- Can reset the current day so that it reuses the week template.

### Reset and capacity limit

- "Reset All" will delete the current user's weekly template version and all single-day customizations, and restore the system default template.
- If modifying or resetting the time grid will cause the time period of the existing arrangement to become invalid, the system will refuse to save it.
- The total scheduled time of each time grid cannot exceed the grid capacity. For example, the capacity of 18:00-18:40 is 40 minutes. If 30 minutes have been scheduled, only 10 more minutes can be scheduled at most.

## Subject template

When adding or editing tasks, the "Account" field supports drop-down selection and direct input.

There is "Edit Account Template" at the bottom of the drop-down list. After entering you can:

- Enable or disable default accounts.
- Add a custom account.
- Delete a custom account.
- Save the template.

The rules are as follows:

- Default accounts are not deleted, only enabled or disabled.
- Custom account names can be up to 40 characters long.
- Account names will have leading and trailing spaces removed and will be deduplicated in a case-insensitive manner.
- The account saved by the task is ordinary text and does not have to come from a template. Therefore, the template only affects the drop-down list and does not automatically change the saved tasks.

## Feedback

After logging in, you can click the "Feedback" button in the upper right area of ​​the page.

### Submit feedback

Feedback content can be up to 1000 characters. Can fill in:

- Problems encountered.
- areas for improvement.
- Questions about page display or operation.

After submission, you can view the history in "My Feedback".

### Feedback status and upper limit

Each feedback has two statuses:

- Pending reply: The administrator has not replied yet.
- Replied: The administrator has filled in the reply.

The system limits the number of "unanswered feedback", not the total number of feedback. That is to say:

- When the number of unanswered feedback reaches the upper limit, new feedback cannot be submitted.
- After the administrator replies, the feedback will no longer occupy the unanswered quota.
- You can also delete old feedback to release quota; deleting feedback will also delete the administrator's reply.

## Theme and layout

- The page supports switching between light and dark themes.
- The left sidebar can be collapsed or expanded.
- The shortcut buttons and the current number of task pools will still be retained after the sidebar is collapsed.
- On narrow screens or mobile devices, the sidebar is more compact by default to leave space for the main timeline and daily schedule.

## Administrator backend

After logging in with an administrator account, you can open the Admin panel from the account menu. It is available only to users with the `admin` role.

### Enter and exit

- After entering the background, the page switches to the administrator layout.
- You can switch between different management modules on the left side of the background.
- Click to exit the background to return to the normal to-do page.

When entering the administrator background, the system will record an "administrator background" access.

### User list

"User List" is used to view the basic information of all users, including:

- User name.
- Nickname.
- character.
- Number of tasks.
- Daily scheduled quantity.
- Last activity time.

Administrators can edit user names and delete users. Deleting a user will delete the user's tasks, daily schedule, time grid configuration, feedback and other related data. The currently logged in administrator account cannot delete itself.

### User log

"User Log" requires you to select a user first and then view the user's operation records. Logs cover common operations such as:

- Register and log in.
- Add, update, complete, uncomplete and delete tasks.
- Add, update, complete, uncomplete and delete daily schedules.
- Update time grid template, single day time grid, reset time grid.
- Modify nickname and password.
- Submit or delete feedback.
- Administrator replies or deletes feedback.
- Update account template.

The log is used to troubleshoot problems and understand operation history. It is not a to-do entry for ordinary users.

### User feedback

"User Feedback" is used to centrally handle all user-submitted feedback.

Administrators can:

- View the feedback submitter, feedback content, status, submission time and administrator response.
- Reply to feedback.
- The editor has replied.
- Remove feedback.
- Set a maximum limit for unanswered feedback per user.

Unanswered feedback limit must be an integer between 1 and 1000. This upper limit only counts feedback that needs to be responded to, and feedback that has been responded to does not count towards the quota.

### Traffic Statistics

"Traffic statistics" counts page visits on the homepage and administrator backend, excluding static resources and ordinary API requests.

to view:

- Total visits.
- Visited today.
- Dedicated IP.
- Today's independent IPs.
- Access trend line charts.
- Popular IPs.
- Recent access history.

The trend chart supports four time ranges:

- 30 days.
- 7 days.
- 1 day.
- 6 hours.

Recent access records will display the accessed page, IP, user, path and access time. You can filter by all access, anonymous access or specific users; there is no user information for unlogged access.

### User schedule

"User Schedule" is used to read-only view a user's tasks and schedules.

How to use:

1. Select the user first.
2. Click to refresh the schedule.
3. View the user's "DDL Date Timeline" and "Daily Schedule" in the home page format.

This view is read-only, and administrators cannot directly drag, edit, or delete tasks for users here.

## Common limitations

- Tasks, schedules, feedback or time grid settings cannot be saved while not logged in.
- Task title and account cannot be empty.
- When setting the deadline, both the date and time must be filled in.
- Time format supports `H:mm` or `HH:mm`.
- The daily schedule cannot exceed the capacity of the target time grid.
- Canceling a DDL completion does not automatically cancel the associated scheduled completion.
- Deleting a DDL task will delete the associated schedule, deleting a single schedule will not delete the original task.
- Feedback submission is subject to the upper limit of "unanswered feedback", and replied feedback does not count towards the quota.
