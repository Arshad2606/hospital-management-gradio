import gradio as gr
import uuid
from datetime import datetime
import tempfile
from textwrap import wrap

# Updated for Gradio 6.x
# Upgrade with:  pip install --upgrade gradio

# ────────────────────────────────────────────────────────
# 1. DATABASE & INITIALIZATION LAYER
# ────────────────────────────────────────────────────────
DOCTORS = {
    "Cardiology": ["Dr. Sarah Jenkins (Room 401)", "Dr. Alan Mercer (Room 402)"],
    "Pediatrics": ["Dr. Evelyn Ross (Room 105)", "Dr. Nathan Vance (Room 106)"],
    "General Medicine": ["Dr. Lisa Chang (Room 210)", "Dr. Marcus Brody (Room 211)"],
    "Orthopedics": ["Dr. Roger Croft (Room 305)", "Dr. Diana Prince (Room 306)"],
}

# ── Background image ──────────────────────────────────
# Save a hospital photo next to this .py file and name it grd_image2.jpg
# (jpg, jpeg, png or webp all work; change the name below if needed).
import base64
import mimetypes
from pathlib import Path

_CANDIDATES = [Path(__file__).parent / "grd_image2.jpg"]
BG_FILE = _CANDIDATES[0]

def build_css():
    if BG_FILE.exists():
        mime = mimetypes.guess_type(BG_FILE.name)[0] or "image/jpeg"
        data = base64.b64encode(BG_FILE.read_bytes()).decode()
        bg = f"url('data:{mime};base64,{data}')"
    else:
        print(f"[!] Background image not found: {BG_FILE}  (using a plain blue gradient)")
        bg = "linear-gradient(135deg, #cfe8ff, #eaf6ff)"
    return f"""
    body::before {{
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        z-index: -1;
        background-image: {bg};
        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
    }}
    gradio-app, .gradio-container, .app, .main, body {{
        background: transparent !important;
    }}
    #title-box, #main-wrap {{
        background: rgba(255,255,255,.85) !important;
        border-radius: 14px;
        padding: 14px 18px;
        color: #1a202c;
    }}
    #title-box {{ margin-bottom: 12px; }}
    """


FORCE_LIGHT_JS = "() => { document.body.classList.remove('dark'); }"


class HospitalDatabase:
    def __init__(self):
        # Pre-populate some demo data for immediate testing
        self.patients = {
            "PAT-1001": {
                "id": "PAT-1001",
                "name": "Alice Henderson",
                "age": 34,
                "gender": "Female",
                "phone": "555-0199",
                "symptom": "Chronic headaches and mild light sensitivity.",
            },
            "PAT-1002": {
                "id": "PAT-1002",
                "name": "Marcus Vance",
                "age": 45,
                "gender": "Male",
                "phone": "555-0211",
                "symptom": "Recurring knee pain after athletic training.",
            },
        }
        self.appointments = [
            {
                "id": "APT-5001",
                "patient_id": "PAT-1001",
                "patient_name": "Alice Henderson",
                "doctor": "Dr. Lisa Chang (Room 210)",
                "department": "General Medicine",
                "datetime": "2026-09-10 at 10:00 AM",
                "status": "Confirmed",
            }
        ]


db = HospitalDatabase()


def patient_choices():
    return [f"{pid} | {d['name']}" for pid, d in db.patients.items()]


def appointment_choices():
    return [
        f"{a['id']} | {a['patient_name']} | {a['datetime']}"
        for a in db.appointments
        if a["status"] == "Confirmed"
    ]


# ────────────────────────────────────────────────────────
# 2. CONTROLLER LOGIC FUNCTIONS
# ────────────────────────────────────────────────────────
def register_patient(name, age, gender, phone, symptom):
    if not name or not name.strip() or not phone or not phone.strip():
        return gr.update(value="### ❌ Error: Name and Phone are required!", visible=True), gr.update()

    patient_id = f"PAT-{uuid.uuid4().hex[:4].upper()}"
    db.patients[patient_id] = {
        "id": patient_id,
        "name": name.strip(),
        "age": int(age) if age is not None else 0,
        "gender": gender,
        "phone": phone.strip(),
        "symptom": symptom or "Not provided",
    }

    msg = "\n".join([
        "### ✅ Patient Registered Successfully!",
        f"* **Patient ID:** `{patient_id}`",
        f"* **Name:** {name.strip()}",
        "* **Department assigned:** General Medicine triage",
    ])
    return gr.update(value=msg, visible=True), gr.update(choices=patient_choices())


def update_doctors(department):
    doctors = DOCTORS.get(department, [])
    return gr.update(choices=doctors, value=doctors[0] if doctors else None)


def book_appointment(patient_select, department, doctor, date, time):
    if not patient_select:
        return "### ❌ Error: Please select a patient first!"
    if not doctor or not date or not time:
        return "### ❌ Error: Please choose a doctor, date and time slot!"

    try:
        datetime.strptime(date.strip(), "%Y-%m-%d")
    except ValueError:
        return "### ❌ Error: Date must be in YYYY-MM-DD format (example: 2026-10-05)."

    apt_time = f"{date.strip()} at {time}"

    # Prevent double-booking the same doctor at the same time
    for a in db.appointments:
        if a["doctor"] == doctor and a["datetime"] == apt_time and a["status"] == "Confirmed":
            return f"### ⚠️ {doctor} is already booked at {apt_time}. Please choose another slot."

    patient_id = patient_select.split(" | ")[0]
    patient_name = db.patients[patient_id]["name"]
    apt_id = f"APT-{uuid.uuid4().hex[:4].upper()}"

    db.appointments.append({
        "id": apt_id,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "doctor": doctor,
        "department": department,
        "datetime": apt_time,
        "status": "Confirmed",
    })

    return "\n".join([
        "### 📅 Appointment Booked Successfully!",
        f"* **Appointment ID:** `{apt_id}`",
        f"* **Patient Name:** {patient_name} (`{patient_id}`)",
        f"* **Assigned Specialist:** {doctor}",
        f"* **Scheduled Time:** {apt_time}",
        "* **Location:** Outpatient Wing (Building B)",
    ])


def load_patient_records(query=""):
    """All patients, or only those matching the search text."""
    q = (query or "").strip().lower()
    rows = []
    for pid, d in db.patients.items():
        haystack = f"{pid} {d['name']} {d['phone']} {d['symptom']}".lower()
        if q and q not in haystack:
            continue
        rows.append([pid, d["name"], d["age"], d["gender"], d["symptom"]])
    return rows


def load_appointment_records():
    return [
        [a["id"], a["patient_id"], a["patient_name"], a["doctor"], a["datetime"], a["status"]]
        for a in db.appointments
    ]


def refresh_all(query):
    return (
        load_patient_records(query),
        load_appointment_records(),
        gr.update(choices=appointment_choices(), value=None),
    )


def cancel_appointment(selection):
    if not selection:
        return "### ❌ Error: Select an appointment to cancel!", gr.update(), load_appointment_records()

    apt_id = selection.split(" | ")[0]
    msg = f"### ❌ Appointment `{apt_id}` was not found."
    for a in db.appointments:
        if a["id"] == apt_id:
            a["status"] = "Cancelled"
            msg = "\n".join([
                "### 🗑️ Appointment Cancelled",
                f"* **Appointment ID:** `{apt_id}`",
                f"* **Patient:** {a['patient_name']}",
                f"* **Was scheduled:** {a['datetime']} with {a['doctor']}",
            ])
            break

    return msg, gr.update(choices=appointment_choices(), value=None), load_appointment_records()


def create_invoice_file(invoice_id, p, patient_id, meds, consult, treatment, tax, total):
    """Create a downloadable invoice. PDF if reportlab is installed, otherwise a .txt file."""
    out_dir = Path(tempfile.gettempdir())
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        ("METROPOLITAN HOSPITAL CENTER", 18, True),
        ("MEDICAL PRESCRIPTION & INVOICE", 12, True),
        ("", 10, False),
        (f"Invoice: {invoice_id}    Date: {date_str}", 11, False),
        ("", 10, False),
        ("PATIENT", 12, True),
        (f"Name: {p['name']}", 11, False),
        (f"Patient ID: {patient_id}    Gender/Age: {p['gender']} ({p['age']} years)", 11, False),
        (f"Clinical presentation: {p['symptom']}", 11, False),
        ("", 10, False),
        ("PRESCRIPTION", 12, True),
    ]
    for raw in meds.splitlines() or [meds]:
        for part in wrap(raw, 85) or [""]:
            lines.append((part, 11, False))
    lines += [
        ("", 10, False),
        ("CHARGES", 12, True),
        (f"Consultation fee: ${consult:.2f}", 11, False),
        (f"Treatment fee: ${treatment:.2f}", 11, False),
        (f"Medical levy / tax (8%): ${tax:.2f}", 11, False),
        ("", 10, False),
        (f"TOTAL AMOUNT PAYABLE: ${total:.2f}", 13, True),
        ("Status: Pending Payment / Insurance Pre-Auth Checked", 11, False),
    ]

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        path = out_dir / f"{invoice_id}.txt"
        path.write_text("\n".join(t for t, _, _ in lines), encoding="utf-8")
        return str(path)

    path = out_dir / f"{invoice_id}.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    _, height = A4
    y = height - 60
    for text, size, bold in lines:
        if y < 60:
            pdf.showPage()
            y = height - 60
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(50, y, text)
        y -= size + 8
    pdf.save()
    return str(path)


def generate_billing_prescription(patient_select, medicines, treatment_fees, consult_fees):
    if not patient_select:
        return "### ❌ Error: Select a patient to process billing!", None

    patient_id = patient_select.split(" | ")[0]
    p = db.patients[patient_id]

    treatment_fees = float(treatment_fees or 0)
    consult_fees = float(consult_fees or 0)
    subtotal = treatment_fees + consult_fees
    tax = subtotal * 0.08  # 8% medical service levy
    total_due = subtotal + tax
    meds = medicines.strip() if medicines and medicines.strip() else "No active prescriptions written."
    invoice_id = f"INV-{uuid.uuid4().hex[:6].upper()}"

    meds_md = "  \n".join(meds.splitlines())
    md = "\n".join([
        "# 🏥 METROPOLITAN HOSPITAL CENTER",
        "**MEDICAL PRESCRIPTION & INVOICE**",
        "",
        "---",
        "",
        f"**Invoice Reference:** {invoice_id} | **Date:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "### 👥 Patient Profile",
        f"* **Patient Name:** {p['name']}",
        f"* **Patient ID:** `{patient_id}` | **Gender/Age:** {p['gender']} ({p['age']} years)",
        f"* **Clinical Presentation:** {p['symptom']}",
        "",
        "### 💊 Treatment & Prescription Instructions",
        meds_md,
        "",
        "### 💰 Itemized Financial Breakdown",
        f"* **Standard Consultation Fee:** ${consult_fees:.2f}",
        f"* **Specialist Treatment Fee:** ${treatment_fees:.2f}",
        f"* **Medical Levy / Sales Tax (8%):** ${tax:.2f}",
        "",
        "---",
        "",
        f"**TOTAL AMOUNT PAYABLE:** ${total_due:.2f}",
        "",
        "**Status:** Pending Payment / Insurance Pre-Auth Checked",
        "",
        "*Please present this copy at the Pharmacy counter and the Billing Desk.*",
    ])

    file_path = create_invoice_file(invoice_id, p, patient_id, meds, consult_fees, treatment_fees, tax, total_due)
    return md, file_path


# ────────────────────────────────────────────────────────
# 3. GRADIO BLOCKS USER INTERFACE DESIGN
# ────────────────────────────────────────────────────────
with gr.Blocks(title="Metropolitan Hospital HMS") as demo:
    gr.Markdown(
        "# 🏥 METROPOLITAN HOSPITAL ADMINISTRATIVE PORTAL\n"
        "*Stateful outward-facing clinic registry and specialist booking desk.*",
        elem_id="title-box",
    )

    with gr.Tabs(elem_id="main-wrap"):

        # TAB 1: PATIENT REGISTRATION
        with gr.Tab("📝 Patient Registration"):
            gr.Markdown("### Add a New Patient to the In-Memory Database")
            with gr.Row():
                with gr.Column():
                    name_in = gr.Textbox(label="Patient Full Name", placeholder="John Doe")
                    age_in = gr.Number(label="Age", value=30, precision=0)
                    gender_in = gr.Radio(label="Gender", choices=["Male", "Female", "Other"], value="Male")
                    phone_in = gr.Textbox(label="Contact Number", placeholder="555-0100")
                with gr.Column():
                    symptom_in = gr.Textbox(
                        label="Admitting Symptoms / Notes", lines=5,
                        placeholder="Describe clinical presentation...",
                    )
                    register_btn = gr.Button("Register Patient", variant="primary")

            registration_output = gr.Markdown(visible=False)

        # TAB 2: SPECIALIST BOOKING
        with gr.Tab("📅 Book Specialist Appointment"):
            gr.Markdown("### Schedule a Consultation with an Active Medical Practitioner")
            with gr.Row():
                with gr.Column():
                    patient_select = gr.Dropdown(label="Select Registered Patient", choices=patient_choices())
                    dept_select = gr.Dropdown(
                        label="Target Department",
                        choices=list(DOCTORS.keys()),
                        value="General Medicine",
                    )
                    doctor_select = gr.Dropdown(
                        label="Assigned Specialist",
                        choices=DOCTORS["General Medicine"],
                        value=DOCTORS["General Medicine"][0],
                    )
                with gr.Column():
                    apt_date = gr.Textbox(label="Appointment Date (YYYY-MM-DD)", value=datetime.now().strftime('%Y-%m-%d'))
                    apt_time = gr.Dropdown(
                        label="Available Slot",
                        choices=["09:00 AM", "10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM"],
                    )
                    book_btn = gr.Button("Confirm Appointment", variant="primary")

            booking_output = gr.Markdown()
            dept_select.change(fn=update_doctors, inputs=dept_select, outputs=doctor_select)

        # TAB 3: RECORDS VIEWER (search + cancel)
        with gr.Tab("📊 Administration Records"):
            gr.Markdown("### Live In-Memory Administrative Registry Tables")
            with gr.Row():
                search_in = gr.Textbox(
                    label="🔍 Search patients (name, ID, phone or symptom)",
                    placeholder="Type to search...",
                    scale=4,
                )
                refresh_btn = gr.Button("🔄 Refresh Logs", variant="secondary", scale=1)

            gr.Markdown("#### 👥 Patient Directory")
            patient_table = gr.Dataframe(
                headers=["Patient ID", "Full Name", "Age", "Gender", "Symptom Description"],
                value=load_patient_records(),
            )

            gr.Markdown("#### 📅 Appointments List")
            appointment_table = gr.Dataframe(
                headers=["Apt ID", "Patient ID", "Patient Name", "Doctor Assigned", "Datetime", "Status"],
                value=load_appointment_records(),
            )

            gr.Markdown("#### 🗑️ Cancel an Appointment")
            with gr.Row():
                cancel_select = gr.Dropdown(
                    label="Select a confirmed appointment",
                    choices=appointment_choices(),
                    scale=4,
                )
                cancel_btn = gr.Button("Cancel Appointment", variant="stop", scale=1)
            cancel_output = gr.Markdown()

            search_in.change(fn=load_patient_records, inputs=search_in, outputs=patient_table)
            refresh_btn.click(
                fn=refresh_all,
                inputs=search_in,
                outputs=[patient_table, appointment_table, cancel_select],
            )
            cancel_btn.click(
                fn=cancel_appointment,
                inputs=cancel_select,
                outputs=[cancel_output, cancel_select, appointment_table],
            )

        # TAB 4: PRESCRIPTION & BILLING ENGINE
        with gr.Tab("💵 Billing & Prescriptions"):
            gr.Markdown("### Generate Official Patient Prescription & Invoice Card")
            with gr.Row():
                with gr.Column():
                    billing_patient_select = gr.Dropdown(label="Select Patient File", choices=patient_choices())
                    medicines_in = gr.Textbox(
                        label="Prescription & Dosage Details",
                        lines=4,
                        placeholder="E.g., 1. Amoxicillin 500mg - 3x Daily for 7 days\n2. Paracetamol 650mg - PRN for fever",
                    )
                    consult_fees = gr.Number(label="Consultation Fee ($)", value=75.00)
                    treatment_fees = gr.Number(label="Treatment/Procedure Fee ($)", value=120.00)
                    generate_btn = gr.Button("Generate Invoice & Prescription Document", variant="primary")
                with gr.Column():
                    billing_output = gr.Markdown("### Preview Document Output Here")
                    invoice_file = gr.File(label="⬇️ Download invoice")

            generate_btn.click(
                fn=generate_billing_prescription,
                inputs=[billing_patient_select, medicines_in, treatment_fees, consult_fees],
                outputs=[billing_output, invoice_file],
            )

    # Registration refreshes the patient dropdowns and the patient table
    register_btn.click(
        fn=register_patient,
        inputs=[name_in, age_in, gender_in, phone_in, symptom_in],
        outputs=[registration_output, patient_select],
    ).then(
        fn=lambda: (gr.update(choices=patient_choices()), load_patient_records()),
        inputs=[],
        outputs=[billing_patient_select, patient_table],
    )

    # Booking refreshes the appointments table and the cancel list
    book_btn.click(
        fn=book_appointment,
        inputs=[patient_select, dept_select, doctor_select, apt_date, apt_time],
        outputs=booking_output,
    ).then(
        fn=lambda: (load_appointment_records(), gr.update(choices=appointment_choices(), value=None)),
        inputs=[],
        outputs=[appointment_table, cancel_select],
    )

if __name__ == "__main__":
    # Set share=True to generate a temporary public link.
    demo.launch(
        theme=gr.themes.Soft(primary_hue="blue"),
        css=build_css(),
        js=FORCE_LIGHT_JS,
        allowed_paths=[tempfile.gettempdir()],
    )