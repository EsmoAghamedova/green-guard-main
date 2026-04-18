# Green Guard - Competition Submission

Green Guard is a role-based reforestation and anti-deforestation web platform.

It combines:

- Sponsorship funding (individual + business)
- Volunteer campaign participation
- Geo-tagged environmental reporting
- Admin verification and moderation
- Public impact visibility through maps and leaderboards

This repository is prepared to help judges evaluate product quality, technical structure, and real-world usability quickly.

## 1. Competition Pitch

Deforestation platforms often fail because trust and execution are disconnected.

Green Guard connects four critical loops in one product:

1. Funding loop: sponsors and businesses provide resources.
2. Action loop: volunteers plant trees and join campaigns.
3. Oversight loop: community reports possible cutting incidents.
4. Governance loop: admin verifies users, moderates reports, and controls quality.

Result: measurable environmental action with accountability.

## 2. Judge Quick Demo (10-15 Minutes)

If you only have a few minutes, follow this exact sequence:

1. Start the app and log in as admin.
2. Register one Volunteer account and one Business account.
3. Confirm those two accounts are blocked by verification pending status.
4. As admin, approve both accounts from Admin Users.
5. Log in as Volunteer and request to join a campaign.
6. Log in as Business and create sponsorship/donation records.
7. Return to admin dashboard to review campaign requests, donations, and report moderation.
8. Open map and leaderboard pages to verify impact visibility.

This demonstrates the complete trust and action pipeline end-to-end.

## 3. Core Roles

- Admin: platform governance, verification, moderation, finance oversight.
- Volunteer: joins campaigns, contributes field activity.
- Business: funds efforts and appears in sponsor impact views.
- Individual Sponsor: personal donor role (shown in UI as Sponsor/Individual).

Note: in code/data, Sponsor is represented by role value `individual`.

## 4. Verification System (Important for Judges)

Green Guard includes a role-sensitive user verification system:

- Volunteer and Business accounts require admin approval.
- Until approved, those users are redirected to a Verification Pending page.
- Admin can mark accounts as `approved`, `pending`, or `rejected`.
- Individual Sponsor accounts are approved by default.

Why this matters in competition terms:

- Prevents fake operational accounts in sensitive flows.
- Adds governance and trust scoring to the platform design.
- Demonstrates secure role lifecycle, not just UI role switching.

## 5. Product Flow

### 5.1 User Lifecycle Flow

1. User registers and selects role.
2. If role is Volunteer or Business, status starts as pending.
3. User can log in but is limited to verification screen/settings/logout.
4. Admin reviews and approves/rejects account.
5. Approved user accesses role-specific dashboard and features.

### 5.2 Campaign Participation Flow

1. Volunteer browses campaigns.
2. Volunteer submits join request.
3. Admin/campaign owner approves request.
4. Volunteer submits campaign planting records.

### 5.3 Sponsorship Flow

1. Sponsor/Business opens donation page.
2. Selects category/item/amount/quantity.
3. Payment flow stores donation record.
4. Impact contributes to sponsor leaderboard and finance views.

### 5.4 Reporting Flow

1. User submits cutting report with coordinates and optional anonymity.
2. Report status enters moderation queue.
3. Admin updates status (pending/reviewed/resolved/rejected).
4. Moderated data appears in public visibility layers where applicable.

## 6. Project Structure

```text
green-guard-main/
|- app.py                    # Flask app factory, schema compatibility, startup
|- models.py                 # SQLAlchemy domain models
|- forms.py                  # WTForms validation and user input contracts
|- permissions.py            # Role-based and verification-based access rules
|- extensions.py             # DB/login manager instances
|- seed_test_data.py         # Optional sample records for map/reports
|- routes/
|  |- auth.py                # Register/login/settings/verification pending
|  |- admin.py               # Admin dashboard, users, status controls
|  |- main.py                # Main pages, campaigns, donations, leaderboard logic
|  |- reports.py             # Reporting and planting report handlers
|  \- volunteer.py           # Volunteer campaign exploration and joins
|- templates/                # Jinja templates grouped by domain
|- static/                   # CSS, JS, media assets
\- requirements.txt          # Python dependencies
```

## 7. Tech Stack

- Backend: Flask
- Auth: Flask-Login
- ORM/DB: SQLAlchemy + SQLite
- Forms/Validation: Flask-WTF + WTForms
- Frontend: Jinja templates + Tailwind/Bootstrap styling patterns

## 8. Local Setup and Run

### 8.1 Requirements

- Python 3.10+
- pip

### 8.2 Install

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 8.3 Run

```bash
python app.py
```

Open: http://127.0.0.1:5000

## 9. Test Accounts for Judges

## 9.1 Default Admin (auto-created)

On first run, admin is auto-created if missing:

- Username: `admin`
- Email: `admin@greenguard.local`
- Password: `admin123`

You can override with env vars before startup:

- `ADMIN_USERNAME`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

## 9.2 Recommended Demo Accounts

Create these from Register page:

1. Volunteer
   - Username: `judge_volunteer`
   - Email: `judge_volunteer@example.com`
   - Role: `Volunteer`
   - Password: `JudgeDemo@123`

2. Business
   - Username: `judge_business`
   - Email: `judge_business@example.com`
   - Role: `Business / Company`
   - Password: `JudgeDemo@123`

3. Sponsor (Individual)
   - Username: `judge_sponsor`
   - Email: `judge_sponsor@example.com`
   - Role: `Individual Sponsor`
   - Password: `JudgeDemo@123`

Admin approval step:

1. Log in as admin.
2. Go to Admin -> Users.
3. Set Volunteer and Business to `Approved`.
4. Sponsor/Individual can operate immediately.

## 10. How to Use the Site (Judge-Oriented)

### 10.1 As Admin

- Review account verification queue.
- Approve/reject Volunteer and Business users.
- Moderate cutting reports.
- Review campaign and finance summaries.

### 10.2 As Volunteer

- Explore campaigns.
- Submit join requests.
- Participate in approved campaign activity.

### 10.3 As Business

- Access sponsorship/donation flows.
- Contribute funding tied to measurable outcomes.
- Observe ranking/impact changes.

### 10.4 As Sponsor (Individual)

- Donate to planting-related categories.
- Engage with leaderboard and impact views.

## 11. Key Evaluation Strengths

- End-to-end multi-role platform, not a single-page prototype.
- Governance-first design with verification gate.
- Practical moderation pipeline for sensitive reports.
- Transparent impact surfaces (leaderboards, dashboards, map).
- Backward-compatible schema updates without requiring migrations.

## 12. Data and Safety Notes

- Role and verification checks run server-side, not only in UI.
- Pending/rejected users are restricted from protected routes.
- Report lifecycle supports moderation before broad visibility.
- Passwords are hashed via Werkzeug security utilities.

## 13. Optional: Add Sample Environmental Records

To seed sample trees/reports for map/testing:

```bash
python seed_test_data.py
```

## 14. Troubleshooting

- If login works but user cannot navigate: check verification status in Admin Users.
- If command line activation is blocked on Windows PowerShell: run with process-level execution policy.
- If app starts with an older database file: startup includes compatibility column creation for key schema updates.

## 15. Ethics Statement

Green Guard is designed around trustworthy environmental action. Sensitive reporting is moderated to reduce harm from false claims, and role verification limits misuse in operational flows. The platform avoids selling user data and emphasizes transparent impact through visible activity and funding outcomes. By combining community reporting, volunteer execution, and sponsor financing under admin governance, the system prioritizes both ecological impact and responsible digital participation.
