- [ ] Add logic to redirect superusers to admin dashboard regardless of `role`
- [ ] Update `attendance/views.py` dashboard() to prioritize `user.is_superuser` (and/or `is_staff`)
- [ ] (Optional) Update admin_reports permission to allow superusers
- [ ] Run server + verify: login as superuser lands on `admin_dashboard.html`

