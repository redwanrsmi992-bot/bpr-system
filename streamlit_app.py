import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from flask import Flask
from models import db, Employee, Process, Step
import io

# ---- حماية بكلمة مرور ----
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("نظام إعادة هندسة العمليات")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### دخول اعضاء الفريق")
        password = st.text_input("ادخل كلمة المرور", type="password")
        if st.button("دخول", use_container_width=True):
            if password == "BPR2026":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("كلمة المرور خاطئة")
        st.markdown("---")
        st.caption("للاستفسار عن كلمة المرور، تواصل مع مسؤول النظام")
    st.stop()

# ---- التطبيق الرئيسي ----
st.set_page_config(page_title="نظام إعادة هندسة العمليات", layout="wide")
st.title("نظام إعادة هندسة العمليات - دائرة الموازنة العامة")

if st.sidebar.button("تسجيل الخروج"):
    st.session_state.authenticated = False
    st.rerun()

# ---- إعداد قاعدة البيانات ----
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bpr_system.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# ---- دوال مساعدة ----
def get_processes():
    with app.app_context():
        processes = Process.query.all()
        for p in processes:
            _ = p.steps
        return processes

def get_process_by_id(pid):
    with app.app_context():
        p = Process.query.get(pid)
        if p:
            _ = p.steps
        return p

def get_steps(pid):
    with app.app_context():
        return Step.query.filter_by(process_id=pid).order_by(Step.step_order).all()

def add_process_to_db(name, category, freq, status):
    with app.app_context():
        p = Process(name=name, category=category, annual_frequency=freq, status=status)
        db.session.add(p)
        db.session.commit()

def update_process_in_db(pid, name, category, freq, status):
    with app.app_context():
        p = Process.query.get(pid)
        if p:
            p.name = name
            p.category = category
            p.annual_frequency = freq
            p.status = status
            db.session.commit()
            return True
        return False

def delete_process_from_db(pid):
    with app.app_context():
        p = Process.query.get(pid)
        if p:
            db.session.delete(p)
            db.session.commit()
            return True
        return False

def add_employee_to_db(title, cost):
    with app.app_context():
        e = Employee(title=title, monthly_cost=cost)
        db.session.add(e)
        db.session.commit()

def update_employee_in_db(eid, title, cost):
    with app.app_context():
        e = Employee.query.get(eid)
        if e:
            e.title = title
            e.monthly_cost = cost
            db.session.commit()
            return True
        return False

def delete_employee_from_db(eid):
    with app.app_context():
        e = Employee.query.get(eid)
        if e:
            db.session.delete(e)
            db.session.commit()
            return True
        return False

def get_employees():
    with app.app_context():
        return Employee.query.all()

def add_step_to_db(pid, eid, order, name, pt, wt, stype, sys_used, waste):
    with app.app_context():
        s = Step(process_id=pid, employee_id=eid, step_order=order,
                 step_name=name, processing_time_minutes=pt,
                 wait_time_minutes=wt, step_type=stype,
                 system_used=sys_used, waste_category=waste)
        db.session.add(s)
        db.session.commit()

# ---- القائمة الجانبية ----
menu = st.sidebar.radio("القائمة", [
    "الرئيسية",
    "اضافة موظف",
    "اضافة عملية",
    "اضافة خطوات",
    "لوحة التحكم",
    "رحلة العميل",
    "مصفوفة الاثر والتاثير",
    "رفع ملف عمليات",
    "🎯 تحليل باريتو (80/20)",
    "📋 SIPOC",
    "📊 RACI",
    "دليل الاستخدام"
])
# ================== الصفحة الرئيسية ==================
if menu == "الرئيسية":
    st.subheader("قائمة العمليات")
    
    processes = get_processes()
    if processes:
        for p in processes:
            with app.app_context():
                eff = Process.query.get(p.id).flow_efficiency
                cost = Process.query.get(p.id).annual_cost
            with st.expander(f"{p.id} - {p.name} ({p.category})"):
                col1, col2, col3 = st.columns(3)
                col1.metric("كفاءة التدفق", f"{eff:.2f}%")
                col2.metric("التكلفة السنوية", f"{cost:,.2f} د.ا")
                col3.metric("التكرار السنوي", p.annual_frequency)
    else:
        st.info("لا توجد عمليات بعد.")

    # ---- استيراد وتصدير ----
    with st.expander("💾 حفظ واستعادة البيانات", expanded=False):
        st.markdown("لتجنب فقدان البيانات، حمّل نسخة احتياطية قبل إعادة النشر.")
        col_backup, col_restore = st.columns(2)
        
        with col_backup:
            if st.button("📥 تحميل نسخة احتياطية (Excel)"):
                with app.app_context():
                    emp_data = [{"id": e.id, "title": e.title, "cost": e.monthly_cost} for e in Employee.query.all()]
                    proc_data = [{"id": p.id, "name": p.name, "category": p.category, "freq": p.annual_frequency, "status": p.status} for p in Process.query.all()]
                    step_data = [{"id": s.id, "process_id": s.process_id, "employee_id": s.employee_id, "order": s.step_order, "name": s.step_name, "pt": s.processing_time_minutes, "wt": s.wait_time_minutes, "type": s.step_type, "system": s.system_used, "waste": s.waste_category} for s in Step.query.all()]
                    
                    df_emp = pd.DataFrame(emp_data) if emp_data else pd.DataFrame()
                    df_proc = pd.DataFrame(proc_data) if proc_data else pd.DataFrame()
                    df_step = pd.DataFrame(step_data) if step_data else pd.DataFrame()
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        if not df_emp.empty: df_emp.to_excel(writer, sheet_name='employees', index=False)
                        if not df_proc.empty: df_proc.to_excel(writer, sheet_name='processes', index=False)
                        if not df_step.empty: df_step.to_excel(writer, sheet_name='steps', index=False)
                    output.seek(0)
                    
                    st.download_button("⬇️ تحميل النسخة الاحتياطية", data=output, file_name="bpr_backup.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with col_restore:
            uploaded_backup = st.file_uploader("📤 استعادة من نسخة احتياطية", type="xlsx", key="restore")
            if uploaded_backup is not None:
                if st.button("🔄 استعادة البيانات"):
                    try:
                        with app.app_context():
                            xl = pd.ExcelFile(uploaded_backup)
                            
                            if 'employees' in xl.sheet_names:
                                df_e = pd.read_excel(uploaded_backup, sheet_name='employees')
                                for _, row in df_e.iterrows():
                                    if not Employee.query.get(row['id']):
                                        emp = Employee(id=row['id'], title=row['title'], monthly_cost=row['cost'])
                                        db.session.add(emp)
                            
                            if 'processes' in xl.sheet_names:
                                df_p = pd.read_excel(uploaded_backup, sheet_name='processes')
                                for _, row in df_p.iterrows():
                                    if not Process.query.get(row['id']):
                                        proc = Process(id=row['id'], name=row['name'], category=row['category'], annual_frequency=row['freq'], status=row['status'])
                                        db.session.add(proc)
                            
                            if 'steps' in xl.sheet_names:
                                df_s = pd.read_excel(uploaded_backup, sheet_name='steps')
                                for _, row in df_s.iterrows():
                                    if not Step.query.get(row['id']):
                                        step = Step(id=row['id'], process_id=row['process_id'], employee_id=row['employee_id'], step_order=row['order'], step_name=row['name'], processing_time_minutes=row['pt'], wait_time_minutes=row['wt'], step_type=row['type'], system_used=row['system'], waste_category=row['waste'])
                                        db.session.add(step)
                            
                            db.session.commit()
                            st.success("تم استعادة جميع البيانات بنجاح!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"فشل الاستيراد: {e}")


# ================== اضافة موظف ==================
elif menu == "اضافة موظف":
    st.subheader("ادارة الموظفين")
    
    with st.expander("اضافة موظف جديد", expanded=False):
        with st.form("add_emp"):
            title = st.text_input("المسمى الوظيفي")
            cost = st.number_input("الراتب الشهري (دينار)", min_value=100, value=500)
            if st.form_submit_button("حفظ"):
                if title:
                    add_employee_to_db(title, float(cost))
                    st.success(f"تمت اضافة الموظف: {title}")
                    st.rerun()
                else:
                    st.error("الرجاء ادخال المسمى الوظيفي")
    
    emps = get_employees()
    if emps:
        st.subheader("الموظفون الحاليون")
        for e in emps:
            with st.expander(f"{e.id} - {e.title} ({e.monthly_cost:.0f} د.ا)"):
                if st.button("حذف", key=f"del_emp_{e.id}"):
                    delete_employee_from_db(e.id)
                    st.success("تم الحذف")
                    st.rerun()

# ================== اضافة عملية ==================
elif menu == "اضافة عملية":
    st.subheader("اضافة عملية جديدة")
    with st.form("add_proc"):
        name = st.text_input("اسم العملية")
        category = st.selectbox("الفئة", ["استراتيجية", "انتصار_سريع", "روتينية", "للدراسة"])
        freq = st.number_input("التكرار السنوي", min_value=1, value=1)
        status = st.selectbox("الحالة", ["غير_مبدوء", "تحت_الدراسة", "مكتمل"])
        if st.form_submit_button("حفظ"):
            if name:
                add_process_to_db(name, category, freq, status)
                st.success(f"تمت اضافة العملية: {name}")
                st.rerun()
            else:
                st.error("الرجاء ادخال اسم العملية")

# ================== اضافة خطوات (آمن) ==================
elif menu == "اضافة خطوات":
    st.subheader("ادارة الخطوات")

    tab1, tab2 = st.tabs(["➕ اضافة خطوة", "📋 عرض وتعديل الخطوات"])

    # ---- تبويبة الاضافة ----
    with tab1:
        processes = get_processes()
        employees = get_employees()
        if not processes:
            st.warning("لا توجد عمليات")
        elif not employees:
            st.warning("لا توجد موظفين")
        else:
            pnames = [f"{p.id} - {p.name}" for p in processes]
            enames = [f"{e.id} - {e.title}" for e in employees]
            
            # النموذج الأساسي (Form)
            with st.form("add_step_form"):
                pid_sel = st.selectbox("اختر العملية", pnames)
                eid_sel = st.selectbox("اختر الموظف", enames)
                order = st.number_input("رقم الترتيب", min_value=1, value=1)
                sname = st.text_input("اسم الخطوة")
                pt = st.number_input("وقت المعالجة (دقيقة)", min_value=0.0, value=5.0)
                wt = st.number_input("وقت الانتظار (دقيقة)", min_value=0.0, value=0.0)
                stype = st.selectbox("نوع الخطوة", ["VA", "BNVA", "NVA"])
                system = st.selectbox("النظام المستخدم", ["Oracle", "GFMIS", "Outlook", "ورقي", "يدوي"])
                waste = st.text_input("فئة الهدر (ان وجدت)")
                
                # زر الحفظ (داخل النموذج)
                if st.form_submit_button("💾 حفظ الخطوة"):
                    if sname:
                        pid = int(pid_sel.split(" - ")[0])
                        eid = int(eid_sel.split(" - ")[0])
                        add_step_to_db(pid, eid, order, sname, pt, wt, stype, system, waste)
                        st.success("تمت اضافة الخطوة")
                        st.rerun()
                    else:
                        st.error("الرجاء ادخال اسم الخطوة")
            
            # المساعد (خارج النموذج
            with st.expander("💡 تحليل نوع الخطوة (مساعد)"):
                if sname:
                    st.markdown("""
                    **دليل سريع للتصنيف:**
                    - **VA (قيمة مضافة):** العميل يدفع مقابل هذه الخطوة (مثلاً: تسجيل طلب، إصدار أمر دفع).
                    - **BNVA (هدر ضروري):** إجراء رقابي أو قانوني (مثلاً: تدقيق الرصيد، مراجعة مدير).
                    - **NVA (هدر خالص):** انتظار، إعادة عمل، موافقات زائدة.
                    
                    **اسأل نفسك:** "لو كنت المواطن، هل سأدفع مقابل هذه الخطوة؟"
                    - إذا كان الجواب **نعم** → VA
                    - إذا كان الجواب **لا، لكنها إجبارية** → BNVA
                    - إذا كان الجواب **لا، ويمكن الاستغناء عنها** → NVA
                    """)

    # ---- تبويبة العرض والتعديل ----
    with tab2:
        processes = get_processes()
        if processes:
            pnames = [f"{p.id} - {p.name}" for p in processes]
            sel_process = st.selectbox("اختر العملية لعرض خطواتها", pnames, key="view_steps")
            pid = int(sel_process.split(" - ")[0])
            steps = get_steps(pid)
            
            if steps:
                st.markdown(f"**عدد الخطوات:** {len(steps)}")
                for s in steps:
                    with app.app_context():
                        emp = Employee.query.get(s.employee_id)
                        emp_title = emp.title if emp else "-"
                    with st.expander(f"{s.step_order}. {s.step_name} | {s.step_type} | {emp_title}"):
                        col_info, col_actions = st.columns([3, 1])
                        with col_info:
                            st.markdown(f"""
                            - **الموظف:** {emp_title}
                            - **وقت العمل:** {s.processing_time_minutes} دقيقة
                            - **وقت الانتظار:** {s.wait_time_minutes} دقيقة
                            - **النظام:** {s.system_used or '-'}
                            - **الهدر:** {s.waste_category or '-'}
                            """)
                        with col_actions:
                            # تعديل وحذف (خارج form)
                            if st.button("✏️ تعديل", key=f"edit_step_{s.id}"):
                                st.session_state[f"editing_step_{s.id}"] = True
                            if st.button("🗑️ حذف", key=f"del_step_{s.id}"):
                                with app.app_context():
                                    step = Step.query.get(s.id)
                                    if step:
                                        db.session.delete(step)
                                        db.session.commit()
                                st.success("تم الحذف")
                                st.rerun()
                        
                        if st.session_state.get(f"editing_step_{s.id}", False):
                            with st.form(f"edit_step_form_{s.id}"):
                                employees = get_employees()
                                enames = [f"{e.id} - {e.title}" for e in employees]
                                current_emp = f"{s.employee_id} - {emp_title}" if s.employee_id else enames[0]
                                new_eid_sel = st.selectbox("الموظف", enames, index=enames.index(current_emp) if current_emp in enames else 0)
                                new_order = st.number_input("رقم الترتيب", min_value=1, value=s.step_order)
                                new_name = st.text_input("اسم الخطوة", value=s.step_name)
                                new_pt = st.number_input("وقت المعالجة", min_value=0.0, value=s.processing_time_minutes)
                                new_wt = st.number_input("وقت الانتظار", min_value=0.0, value=s.wait_time_minutes)
                                new_type = st.selectbox("النوع", ["VA", "BNVA", "NVA"], index=["VA", "BNVA", "NVA"].index(s.step_type))
                                new_system = st.selectbox("النظام", ["Oracle", "GFMIS", "Outlook", "ورقي", "يدوي"], index=["Oracle", "GFMIS", "Outlook", "ورقي", "يدوي"].index(s.system_used) if s.system_used in ["Oracle", "GFMIS", "Outlook", "ورقي", "يدوي"] else 0)
                                new_waste = st.text_input("فئة الهدر", value=s.waste_category or "")
                                
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    if st.form_submit_button("💾 حفظ"):
                                        with app.app_context():
                                            step = Step.query.get(s.id)
                                            if step:
                                                step.employee_id = int(new_eid_sel.split(" - ")[0])
                                                step.step_order = new_order
                                                step.step_name = new_name
                                                step.processing_time_minutes = new_pt
                                                step.wait_time_minutes = new_wt
                                                step.step_type = new_type
                                                step.system_used = new_system
                                                step.waste_category = new_waste
                                                db.session.commit()
                                        st.session_state[f"editing_step_{s.id}"] = False
                                        st.success("تم التعديل")
                                        st.rerun()
                                with col_cancel:
                                    if st.form_submit_button("❌ الغاء"):
                                        st.session_state[f"editing_step_{s.id}"] = False
                                        st.rerun()
            else:
                st.info("لا توجد خطوات لهذه العملية")
        else:
            st.info("لا توجد عمليات بعد")
# ================== لوحة التحكم ==================
elif menu == "لوحة التحكم":
    st.subheader("لوحة التحكم")
    processes = get_processes()
    if processes:
        pnames = [f"{p.id} - {p.name}" for p in processes]
        sel = st.selectbox("اختر العملية", pnames)
        pid = int(sel.split(" - ")[0])
        process = get_process_by_id(pid)
        steps = get_steps(pid)
        if process and steps:
            with app.app_context():
                p = Process.query.get(pid)
                eff = p.flow_efficiency
                lead = p.lead_time_minutes
                cost = p.annual_cost
                 # حساب التكلفة الشاملة بطريقة صحيحة
            total_wait_cost = 0
            for s in steps:
                with app.app_context():
                    emp = Employee.query.get(s.employee_id)
                    if emp and s.wait_time_minutes:
                        total_wait_cost += (s.wait_time_minutes * emp.cost_per_minute)
            
            # التكلفة الشاملة = (تكلفة العمل للتنفيذ الواحد + تكلفة الانتظار للتنفيذ الواحد) × التكرار
            cost_per_execution = cost / p.annual_frequency
            comprehensive_annual = (cost_per_execution + total_wait_cost) * p.annual_frequency

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("كفاءة التدفق", f"{eff:.2f}%")
            c2.metric("زمن الدورة (ساعة)", f"{lead/60:.1f}")
            c3.metric("التكلفة السنوية (عمل فقط)", f"{cost:,.2f} د.ا")
            c4.metric("💸 التكلفة الشاملة", f"{comprehensive_annual:,.2f} د.ا")
            sn = [s.step_name for s in steps]
            pt = [s.processing_time_minutes or 0 for s in steps]
            wt = [s.wait_time_minutes or 0 for s in steps]
            bar1 = go.Bar(name='وقت العمل', x=sn, y=pt, marker_color='green')
            bar2 = go.Bar(name='وقت الانتظار', x=sn, y=wt, marker_color='red')
            fig = go.Figure(data=[bar1, bar2])
            fig.update_layout(barmode='stack', xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)
            pie = go.Figure(data=[go.Pie(labels=['عمل', 'انتظار'],
                                          values=[sum(pt), sum(wt)],
                                          marker_colors=['green', 'red'])])
            st.plotly_chart(pie, use_container_width=True)
            tdata = []
            for s in steps:
                with app.app_context():
                    emp = Employee.query.get(s.employee_id)
                    emp_title = emp.title if emp else "-"
                tdata.append({
                    "#": s.step_order,
                    "الخطوة": s.step_name,
                    "الموظف": emp_title,
                    "وقت العمل": s.processing_time_minutes,
                    "وقت الانتظار": s.wait_time_minutes,
                    "النوع": s.step_type,
                    "النظام": s.system_used or "-",
                    "الهدر": s.waste_category or "-"
                })
            st.dataframe(pd.DataFrame(tdata), use_container_width=True)
        else:
            st.info("لا توجد خطوات لهذه العملية")
    else:
        st.info("لا توجد عمليات بعد")

# ================== رحلة العميل ==================
elif menu == "رحلة العميل":
    st.subheader("خريطة رحلة العميل")
    st.markdown("هذه الخريطة توضح رحلة المعاملة من وجهة نظر المواطن او الجهة المستفيدة")
    
    processes = get_processes()
    if processes:
        pnames = [f"{p.id} - {p.name}" for p in processes]
        sel = st.selectbox("اختر العملية لعرض رحلتها", pnames)
        pid = int(sel.split(" - ")[0])
        steps = get_steps(pid)
        process = get_process_by_id(pid)
        
        if steps:
            step_labels = []
            proc_times = []
            wait_times = []
            step_types = []
            pain_scores = []
            
            for s in steps:
                with app.app_context():
                    emp = Employee.query.get(s.employee_id)
                    emp_title = emp.title if emp else "غير محدد"
                
                label = f"{s.step_order}. {s.step_name} - {emp_title}"
                step_labels.append(label)
                proc_times.append(s.processing_time_minutes or 0)
                wait_times.append(s.wait_time_minutes or 0)
                step_types.append(s.step_type)
                
                wait = s.wait_time_minutes or 0
                if wait > 2880:
                    pain_scores.append(10)
                elif wait > 1440:
                    pain_scores.append(8)
                elif wait > 480:
                    pain_scores.append(6)
                elif wait > 60:
                    pain_scores.append(4)
                elif wait > 0:
                    pain_scores.append(2)
                else:
                    pain_scores.append(0)
            
            st.subheader("مراحل الرحلة ونقاط الالم")
            
            fig_journey = go.Figure()
            fig_journey.add_trace(go.Bar(
                name='وقت العمل',
                y=step_labels,
                x=proc_times,
                orientation='h',
                marker=dict(color='#2ecc71'),
                text=[f"{p} دقيقة" if p > 0 else "" for p in proc_times],
                textposition='inside'
            ))
            fig_journey.add_trace(go.Bar(
                name='وقت الانتظار',
                y=step_labels,
                x=wait_times,
                orientation='h',
                marker=dict(color='#e74c3c'),
                text=[f"{w} دقيقة" if w > 0 else "" for w in wait_times],
                textposition='inside'
            ))
            fig_journey.update_layout(
                barmode='stack',
                height=400 + len(steps) * 50,
                title="رحلة المعاملة",
                xaxis_title="الوقت (دقيقة)",
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_journey, use_container_width=True)
            
            # نقاط الالم
            st.subheader("نقاط الالم في الرحلة")
            pain_steps = []
            for i, s in enumerate(steps):
                if pain_scores[i] >= 6:
                    with app.app_context():
                        emp = Employee.query.get(s.employee_id)
                        emp_title = emp.title if emp else "غير محدد"
                    pain_steps.append({
                        "الخطوة": s.step_name,
                        "المسؤول": emp_title,
                        "وقت الانتظار": f"{s.wait_time_minutes:.0f} دقيقة",
                        "درجة الالم": f"{pain_scores[i]}/10",
                        "فئة الهدر": s.waste_category or "غير محدد"
                    })
            
            if pain_steps:
                df_pain = pd.DataFrame(pain_steps)
                st.dataframe(df_pain, use_container_width=True)
                st.error(f"تم اكتشاف {len(pain_steps)} نقاط الم حرجة")
            else:
                st.success("لا توجد نقاط الم حرجة")
            
            # CSAT
            st.subheader("مؤشر رضا العميل التقديري")
            total_proc = sum(proc_times)
            total_wait = sum(wait_times)
            total_time = total_proc + total_wait
            
            if total_time > 0:
                wait_ratio = total_wait / total_time
                csat = max(0, 100 - (wait_ratio * 100))
            else:
                csat = 100
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if csat >= 80:
                    st.markdown(f"<h1 style='color:green; text-align:center;'>{csat:.0f}%</h1>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align:center;'>ممتاز</p>", unsafe_allow_html=True)
                elif csat >= 50:
                    st.markdown(f"<h1 style='color:orange; text-align:center;'>{csat:.0f}%</h1>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align:center;'>متوسط</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<h1 style='color:red; text-align:center;'>{csat:.0f}%</h1>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align:center;'>ضعيف</p>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                **كيف يحسب هذا المؤشر؟**
                - مؤشر رضا العميل = 100% - (نسبة وقت الانتظار من اجمالي زمن الرحلة)
                - اجمالي وقت الرحلة: **{total_time:.0f} دقيقة**
                - وقت العمل الفعلي: **{total_proc:.0f} دقيقة**
                - وقت الانتظار: **{total_wait:.0f} دقيقة**
                """)
            
            # توصيات
            st.subheader("توصيات لتحسين رحلة العميل")
            recommendations = []
            for s in steps:
                with app.app_context():
                    emp = Employee.query.get(s.employee_id)
                    emp_title = emp.title if emp else "غير محدد"
                if s.step_type == 'NVA' and (s.wait_time_minutes or 0) > 1440:
                    recommendations.append(f"اتمتة خطوة '{s.step_name}' (المسؤول: {emp_title}): انتظار {s.wait_time_minutes:.0f} دقيقة يمكن اختزاله")
                elif s.step_type == 'NVA' and (s.wait_time_minutes or 0) > 0:
                    recommendations.append(f"تسريع خطوة '{s.step_name}' (المسؤول: {emp_title})")
                elif s.system_used == 'ورقي':
                    recommendations.append(f"رقمنة خطوة '{s.step_name}' (المسؤول: {emp_title})")
            
            if recommendations:
                for r in recommendations:
                    st.markdown(r)
            else:
                st.success("لا توجد توصيات حالية")
        else:
            st.info("لا توجد خطوات لهذه العملية")
    else:
        st.info("لا توجد عمليات بعد")

# ================== مصفوفة الاثر والتاثير ==================
elif menu == "مصفوفة الاثر والتاثير":
    st.subheader("مصفوفة الاثر والتاثير")
    st.markdown("هذه الاداة تساعدك على التخطيط لتعديل خطوة معينة وتوقع الاثر على باقي اجزاء المنظومة قبل التنفيذ")
    
    processes = get_processes()
    if processes:
        pnames = [f"{p.id} - {p.name}" for p in processes]
        sel_process = st.selectbox("اختر العملية المستهدفة", pnames)
        pid = int(sel_process.split(" - ")[0])
        steps = get_steps(pid)
        
        if steps:
            step_names = [f"{s.step_order}. {s.step_name}" for s in steps]
            
            if "previous_step" not in st.session_state:
                st.session_state.previous_step = step_names[0] if step_names else None
            
            sel_step = st.selectbox("اختر الخطوة التي تريد تعديلها", step_names)
            
            if sel_step != st.session_state.previous_step:
                st.session_state.previous_step = sel_step
                st.session_state.pop("change_desc", None)
                st.rerun()
            
            st.markdown("---")
            st.markdown("### التعديل المقترح")
            change_description = st.text_area("صف التعديل الذي تخطط له", value=st.session_state.get("change_desc", ""))
            
            st.markdown("---")
            st.markdown("### الاطراف المتاثرة بالتعديل")
            
            impacted_parties = ["الموظف", "النظام (Oracle/GFMIS)", "جهة خارجية", "العميل"]
            impacts = {}
            
            for party in impacted_parties:
                with st.expander(f"{party}"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        impact_type = st.selectbox("نوع الاثر", ["لا يوجد تغيير", "تغيير في الصلاحية", "تغيير في الوقت", "تغيير في التكلفة", "مقاومة متوقعة"], key=f"type_{party}")
                    with col2:
                        impact_desc = st.text_area("وصف الاثر", key=f"desc_{party}")
                    impacts[party] = {"type": impact_type, "desc": impact_desc}
            
            st.markdown("---")
            st.markdown("### تقدير مبدئي للعائد")
            selected_step_index = int(sel_step.split(".")[0]) - 1
            if selected_step_index < len(steps):
                target_step = steps[selected_step_index]
                current_wait = target_step.wait_time_minutes or 0
                if current_wait > 0:
                    saved_minutes = current_wait * 0.8
                    st.success(f"بتعديل هذه الخطوة (التي تنتظر {current_wait:.0f} دقيقة)، يمكنك توفير ما يقدر بـ **{saved_minutes:.0f} دقيقة** على الاقل لكل معاملة")
                else:
                    st.info("لا يوجد وقت انتظار مسجل لهذه الخطوة")
            
            if st.button("حفظ التحليل"):
                st.success("تم تسجيل التحليل بنجاح")
        else:
            st.info("لا توجد خطوات لهذه العملية")
    else:
        st.info("لا توجد عمليات بعد")

# ================== رفع ملف عمليات ==================
# ================== رفع ملف عمليات ==================
# ================== رفع ملف عمليات (تلقائي) ==================
elif menu == "رفع ملف عمليات":
    st.subheader("رفع ملف عمليات (Excel/CSV)")
    st.markdown("ارفع ملف Excel أو CSV. سيقرأ النظام أول ورقتين تلقائياً.")

    uploaded_file = st.file_uploader("اختر ملف Excel أو CSV", type=["xlsx", "csv"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_process = pd.read_csv(uploaded_file, nrows=1)
                df_steps = pd.read_csv(uploaded_file, skiprows=2)
            else:
                # قراءة جميع أسماء الأوراق
                xl = pd.ExcelFile(uploaded_file)
                sheet_names = xl.sheet_names
                
                if len(sheet_names) >= 2:
                    df_process = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                    df_steps = pd.read_excel(uploaded_file, sheet_name=sheet_names[1])
                else:
                    st.error("يجب أن يحتوي الملف على ورقتين على الأقل.")
                    st.stop()

            st.subheader("معاينة البيانات المستوردة")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**بيانات العملية:**")
                st.dataframe(df_process, use_container_width=True)
            with col2:
                st.markdown("**بيانات الخطوات:**")
                st.dataframe(df_steps, use_container_width=True)

            if st.button("تاكيد واستيراد البيانات", use_container_width=True):
                with app.app_context():
                    # استيراد العملية
                    process_row = df_process.iloc[0]
                    process_name = str(process_row['اسم العملية'])
                    category = str(process_row.get('الفئة', 'روتينية'))
                    freq = int(process_row.get('التكرار السنوي', 1))
                    status = str(process_row.get('الحالة', 'تحت_الدراسة'))

                    existing = Process.query.filter_by(name=process_name).first()
                    if existing:
                        process_id = existing.id
                        st.info(f"العملية '{process_name}' موجودة مسبقاً. ستُضاف إليها الخطوات.")
                    else:
                        new_process = Process(name=process_name, category=category,
                                             annual_frequency=freq, status=status)
                        db.session.add(new_process)
                        db.session.commit()
                        process_id = new_process.id

                    # استيراد الخطوات
                    steps_added = 0
                    for _, row in df_steps.iterrows():
                        step_order = int(row['رقم الترتيب'])
                        step_name = str(row['اسم الخطوة'])
                        proc_time = float(row.get('وقت المعالجة', 0))
                        wait_time = float(row.get('وقت الانتظار', 0))
                        step_type = str(row.get('النوع', 'VA'))
                        system_used = str(row.get('النظام', ''))
                        waste_cat = str(row.get('فئة الهدر', '')) if pd.notna(row.get('فئة الهدر', None)) else ''
                        emp_name = str(row.get('الموظف', ''))

                        # البحث عن الموظف أو إنشاؤه
                        employee = Employee.query.filter_by(title=emp_name).first()
                        if not employee and emp_name:
                            employee = Employee(title=emp_name, monthly_cost=500)
                            db.session.add(employee)
                            db.session.commit()

                        emp_id = employee.id if employee else None

                        new_step = Step(
                            process_id=process_id,
                            employee_id=emp_id,
                            step_order=step_order,
                            step_name=step_name,
                            processing_time_minutes=proc_time,
                            wait_time_minutes=wait_time,
                            step_type=step_type,
                            system_used=system_used,
                            waste_category=waste_cat
                        )
                        db.session.add(new_step)
                        steps_added += 1

                    db.session.commit()

                st.success(f"تم استيراد العملية '{process_name}' بنجاح مع {steps_added} خطوة!")
                st.balloons()

        except Exception as e:
            st.error("حدث خطأ أثناء قراءة الملف. تأكد من التنسيق الصحيح.")
            st.code(str(e))
# ================== تحليل باريتو ==================
elif menu == "🎯 تحليل باريتو (80/20)":
    st.subheader("🎯 تحليل باريتو للهدر في العمليات")
    st.markdown("هذا التحليل يطبق قاعدة 80/20 لمساعدتك على التركيز على العمليات الأكثر هدراً.")

    all_processes = get_processes()
    if all_processes:
        # 1. تجهيز البيانات
        pareto_data = []
        for proc in all_processes:
            with app.app_context():
                p = Process.query.get(proc.id)
                # حساب الهدر (وقت الانتظار) لكل عملية
                total_wait = sum((s.wait_time_minutes or 0) for s in p.steps)
            pareto_data.append({"name": p.name, "waste": total_wait})
        
        # 2. الترتيب التنازلي
        df_pareto = pd.DataFrame(pareto_data).sort_values(by="waste", ascending=False)
        df_pareto["نسبة مئوية"] = (df_pareto["waste"] / df_pareto["waste"].sum()) * 100
        df_pareto["تراكمي"] = df_pareto["نسبة مئوية"].cumsum()
        
        # 3. الرسم
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Bar(name="وقت الهدر (دقيقة)", x=df_pareto["name"], y=df_pareto["waste"], marker_color="#e74c3c"))
        fig.add_trace(go.Scatter(name="النسبة التراكمية %", x=df_pareto["name"], y=df_pareto["تراكمي"], yaxis="y2", marker_color="#3498db"))
        fig.update_layout(
            title="مخطط باريتو",
            xaxis_title="العمليات",
            yaxis_title="وقت الهدر (دقيقة)",
            yaxis2=dict(title="النسبة التراكمية %", overlaying="y", side="right", range=[0, 100]),
            legend=dict(x=0.01, y=0.99)
        )
        st.plotly_chart(fig)

        # 4. التوصية التلقائية
        st.markdown("---")
        st.subheader("💡 توصية باريتو")
        # تحديد العمليات التي تشكل 80% من الهدر
        vital_few = df_pareto[df_pareto["تراكمي"] <= 80]
        if not vital_few.empty:
            names = "، ".join(vital_few["name"].tolist())
            st.success(f"🎯 **قاعدة 80/20:** التركيز على تحسين هذه العمليات ({names}) سيعالج ما يقارب 80% من إجمالي الهدر.")
        else:
            st.info("حتى الآن، لا توجد عملية واحدة تستحوذ على 80% من الهدر لوحدها.")
    else:
        st.info("لا توجد عمليات بعد لتحليلها.")
        # ================== SIPOC ==================
elif menu == "📋 SIPOC":
    st.subheader("📋 تحليل SIPOC")
    st.markdown("نظرة شاملة للعملية: الموردون، المدخلات، العملية، المخرجات، العملاء.")

    processes = get_processes()
    if processes:
        pnames = [f"{p.id} - {p.name}" for p in processes]
        sel = st.selectbox("اختر العملية", pnames)
        pid = int(sel.split(" - ")[0])
        steps = get_steps(pid)

        if steps:
            # اقتراح تلقائي للبيانات
            suppliers = "جميع الجهات الحكومية (وزارات، دوائر)"
            inputs_list = "طلب مكتمل، مستندات ثبوتية، موافقات سابقة"
            
            # العملية = أسماء الخطوات
            process_desc = " → ".join([s.step_name for s in steps])
            
            outputs_list = "معاملة منجزة، إشعار إلكتروني"
            customers = "المستفيد النهائي، جهة رقابية، ديوان المحاسبة"

            with st.form("sipoc_form"):
                st.subheader("✏️ عدل جدول SIPOC")
                col1, col2 = st.columns(2)
                with col1:
                    sup = st.text_area("**S - الموردون (Suppliers)**", value=suppliers, height=100)
                    inp = st.text_area("**I - المدخلات (Inputs)**", value=inputs_list, height=100)
                    proc = st.text_area("**P - العملية (Process)**", value=process_desc, height=100)
                with col2:
                    outp = st.text_area("**O - المخرجات (Outputs)**", value=outputs_list, height=100)
                    cust = st.text_area("**C - العملاء (Customers)**", value=customers, height=100)

                if st.form_submit_button("💾 حفظ وعرض SIPOC"):
                    st.success("تم تحديث SIPOC")
                    
                    # عرض الجدول النهائي
                    df_sipoc = pd.DataFrame({
                        "المكون": ["S - الموردون", "I - المدخلات", "P - العملية", "O - المخرجات", "C - العملاء"],
                        "الوصف": [sup, inp, proc, outp, cust]
                    })
                    st.dataframe(df_sipoc, use_container_width=True)
        else:
            st.info("لا توجد خطوات لهذه العملية.")
    else:
        st.info("لا توجد عمليات بعد.")
        # ================== RACI Matrix ==================
elif menu == "📊 RACI":
    st.subheader("📊 مصفوفة المسؤوليات (RACI)")
    st.markdown("تحديد المسؤوليات لكل خطوة: Responsible, Accountable, Consulted, Informed")

    processes = get_processes()
    if processes:
        pnames = [f"{p.id} - {p.name}" for p in processes]
        sel = st.selectbox("اختر العملية", pnames)
        pid = int(sel.split(" - ")[0])
        steps = get_steps(pid)

        if steps:
            # جمع كل الموظفين المشاركين في العملية
            unique_emps = {}
            for s in steps:
                with app.app_context():
                    emp = Employee.query.get(s.employee_id)
                    if emp:
                        unique_emps[emp.id] = emp.title

            if unique_emps:
                # اقتراح تلقائي لـ RACI
                st.markdown("### اقتراح آلي (يمكنك تعديله)")
                
                raci_data = []
                for s in steps:
                    with app.app_context():
                        emp = Employee.query.get(s.employee_id)
                        emp_title = emp.title if emp else "-"
                    
                    row = {
                        "الخطوة": s.step_name,
                        "R (مسؤول)": emp_title,
                        "A (معتمد)": "مدير عام" if "توقيع" in s.step_name else "مدير مالي",
                        "C (مُستشار)": "مدقق مالي" if "تدقيق" in s.step_name else "-",
                        "I (مُبلّغ)": "جميع الأطراف"
                    }
                    raci_data.append(row)
                
                df_raci = pd.DataFrame(raci_data)
                
                # عرض قابل للتعديل
                with st.form("raci_form"):
                    edited_rows = []
                    for i, row in enumerate(raci_data):
                        st.markdown(f"**{row['الخطوة']}**")
                        col_r, col_a, col_c, col_i = st.columns(4)
                        with col_r:
                            new_r = st.text_input("R", value=row["R (مسؤول)"], key=f"r_{i}")
                        with col_a:
                            new_a = st.text_input("A", value=row["A (معتمد)"], key=f"a_{i}")
                        with col_c:
                            new_c = st.text_input("C", value=row["C (مُستشار)"], key=f"c_{i}")
                        with col_i:
                            new_i = st.text_input("I", value=row["I (مُبلّغ)"], key=f"i_{i}")
                        edited_rows.append({"الخطوة": row["الخطوة"], "R": new_r, "A": new_a, "C": new_c, "I": new_i})
                    
                    if st.form_submit_button("💾 حفظ RACI"):
                        st.success("تم حفظ مصفوفة RACI")
                        st.dataframe(pd.DataFrame(edited_rows), use_container_width=True)
            else:
                st.info("لا يوجد موظفين مرتبطين بهذه العملية.")
        else:
            st.info("لا توجد خطوات لهذه العملية.")
    else:
        st.info("لا توجد عمليات بعد.")
# ================== دليل الاستخدام ==================
elif menu == "دليل الاستخدام":
    st.subheader("دليل استخدام نظام اعادة هندسة العمليات")
    
    with st.expander("1. الرئيسية", expanded=True):
        st.markdown("""
        **ماذا ترى؟** قائمة بجميع العمليات في صناديق قابلة للطي.
        - كل صندوق يعرض: كفاءة التدفق، التكلفة السنوية، التكرار السنوي.
        - **تعديل:** لتغيير اسم العملية، الفئة، التكرار، او الحالة.
        - **حذف:** لحذف العملية نهائيا.
        """)
    
    with st.expander("2. ادارة الموظفين"):
        st.markdown("""
        **اضافة موظف جديد:**
        - اكتب المسمى الوظيفي.
        - اختر نطاق الراتب من شريط التمرير.
        - يحسب التطبيق المتوسط تلقائيا ويستخدمه في حسابات التكلفة.
        
        **تعديل/حذف موظف:**
        - اضغط تعديل لتغيير المسمى او الراتب.
        - اضغط حذف لحذف الموظف.
        """)
    
    with st.expander("3. اضافة عملية"):
        st.markdown("""
        | الحقل | الوصف |
        |-------|-------|
        | اسم العملية | مثل: المناقلات المالية |
        | الفئة | استراتيجية، انتصار_سريع، روتينية، للدراسة |
        | التكرار السنوي | كم مرة تحدث في السنة |
        | الحالة | غير_مبدوء، تحت_الدراسة، مكتمل |
        """)
    
    with st.expander("4. اضافة خطوات"):
        st.markdown("""
        | الحقل | الوصف | مثال |
        |-------|-------|------|
        | العملية | اختر العملية المستهدفة | المناقلات المالية |
        | الموظف | من يقوم بهذه الخطوة | مدقق مالي |
        | رقم الترتيب | تسلسل الخطوة | 1, 2, 3... |
        | اسم الخطوة | وصف مختصر | انتظار توقيع المدير |
        | وقت المعالجة | دقائق العمل الفعلي | 5 |
        | وقت الانتظار | دقائق الانتظار | 1440 (يوم كامل) |
        | نوع الخطوة | VA = قيمة، BNVA = ضرورية، NVA = هدر |
        | النظام | Oracle, GFMIS, ورقي, Outlook... |
        | فئة الهدر | للخطوات NVA فقط | انتظار، موافقات_زائدة |
        """)
    
    with st.expander("5. لوحة التحكم"):
        st.markdown("""
        اختر عملية لتشاهد:
        - **3 بطاقات:** كفاءة التدفق، زمن الدورة، التكلفة السنوية.
        - **الرسم الشريطي:** اخضر = وقت عمل، احمر = وقت انتظار.
        - **الرسم الدائري:** العمل المفيد مقابل الهدر.
        - **جدول تفصيلي** لجميع الخطوات.
        """)
    
    with st.expander("6. كيف تقرا النتائج؟"):
        st.markdown("""
        | كفاءة التدفق | التقييم | الاجراء |
        |-------------|--------|---------|
        | اقل من 5% | كارثة | تدخل فوري |
        | 5% - 20% | سيء جدا | اولوية للتحسين |
        | 20% - 40% | مقبول | مجال للتحسين |
        | 40% - 60% | جيد | تحسينات طفيفة |
        | اكثر من 60% | ممتاز | حافظ على المستوى |
        """)
    with st.expander("💸 فهم التكاليف (العمل فقط مقابل الشاملة)"):
        st.markdown("""
        ### 📊 نوعان من التكلفة في لوحة التحكم
        
        **1. التكلفة السنوية (عمل فقط):**
        - تحتسب **وقت العمل الفعلي فقط** (Processing Time).
        - المعادلة: مجموع (وقت العمل لكل خطوة × تكلفة الموظف في الدقيقة) × التكرار السنوي.
        - هذا الرقم متحفظ ويعكس فقط الوقت الذي يعمل فيه الموظف فعلياً على المعاملة.
        
        **2. 💸 التكلفة الشاملة:**
        - تحتسب **وقت العمل + وقت الانتظار**.
        - المعادلة: (تكلفة العمل للتنفيذ الواحد + تكلفة الانتظار للتنفيذ الواحد) × التكرار السنوي.
        - هذا الرقم يعكس التكلفة الحقيقية للهدر، حيث أن الموظف يتقاضى راتبه حتى أثناء انتظار المعاملة.
        
        ### 🎯 مثال من عملية المناقلات المالية:
        | المؤشر | القيمة |
        |--------|--------|
        | وقت العمل الفعلي | 32 دقيقة |
        | وقت الانتظار | 4,320 دقيقة (3 أيام) |
        | التكلفة (عمل فقط) | ~686 د.أ سنوياً |
        | التكلفة الشاملة | ~103,000 د.أ سنوياً |
        
        ### 💡 للعرض على الإدارة:
        استخدم **التكلفة الشاملة** لإظهار الحجم الحقيقي للمشكلة.
        استخدم **كفاءة التدفق** لإظهار نسبة الهدر في الوقت.
        """)
    with st.expander("7. نصائح سريعة"):
        st.markdown("""
        - 1440 دقيقة = يوم عمل، 2880 = يومان، 10080 = اسبوع.
        - فئة **انتصار_سريع** = عمليات سهلة تبني سمعتك اولا.
        - كل عملية مكتملة = قصة نجاح للادارة.
        - الهدف: كشف الهدر ثم القضاء عليه.
        """)
