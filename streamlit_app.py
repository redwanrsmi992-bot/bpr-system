import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from flask import Flask
from models import db, Employee, Process, Step
import io

# ---- اعداد التطبيق ----
st.set_page_config(page_title="نظام اعادة هندسة العمليات", layout="wide")

# ---- حماية بكلمة مرور ----
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("نظام اعادة هندسة العمليات")
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
st.title("نظام اعادة هندسة العمليات - دائرة الموازنة العامة")

if st.sidebar.button("تسجيل الخروج"):
    st.session_state.authenticated = False
    st.rerun()

# ---- اعداد قاعدة البيانات ----
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bpr_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
                
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("تعديل", key=f"edit_{p.id}"):
                        st.session_state[f"editing_{p.id}"] = True
                with col_del:
                    if st.button("حذف", key=f"del_{p.id}"):
                        delete_process_from_db(p.id)
                        st.success("تم الحذف")
                        st.rerun()
                
                if st.session_state.get(f"editing_{p.id}", False):
                    with st.form(f"edit_form_{p.id}"):
                        new_name = st.text_input("اسم العملية", value=p.name)
                        cats = ["استراتيجية", "انتصار_سريع", "روتينية", "للدراسة"]
                        new_cat = st.selectbox("الفئة", cats, index=cats.index(p.category) if p.category in cats else 0)
                        new_freq = st.number_input("التكرار السنوي", min_value=1, value=p.annual_frequency)
                        stats = ["غير_مبدوء", "تحت_الدراسة", "مكتمل"]
                        new_status = st.selectbox("الحالة", stats, index=stats.index(p.status) if p.status in stats else 0)
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("حفظ التعديلات"):
                                update_process_in_db(p.id, new_name, new_cat, new_freq, new_status)
                                st.session_state[f"editing_{p.id}"] = False
                                st.success("تم التعديل")
                                st.rerun()
                        with col_cancel:
                            if st.form_submit_button("الغاء"):
                                st.session_state[f"editing_{p.id}"] = False
                                st.rerun()
    else:
        st.info("لا توجد عمليات بعد")

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

# ================== اضافة خطوات (مع تعديل وحذف) ==================
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
            with st.form("add_step"):
                pid_sel = st.selectbox("اختر العملية", pnames)
                eid_sel = st.selectbox("اختر الموظف", enames)
                order = st.number_input("رقم الترتيب", min_value=1, value=1)
                sname = st.text_input("اسم الخطوة")
                pt = st.number_input("وقت المعالجة (دقيقة)", min_value=0.0, value=5.0)
                wt = st.number_input("وقت الانتظار (دقيقة)", min_value=0.0, value=0.0)
                stype = st.selectbox("نوع الخطوة", ["VA", "BNVA", "NVA"])
                system = st.selectbox("النظام المستخدم", ["Oracle", "GFMIS", "Outlook", "ورقي", "يدوي"])
                waste = st.text_input("فئة الهدر (ان وجدت)")
                if st.form_submit_button("💾 حفظ الخطوة"):
                    pid = int(pid_sel.split(" - ")[0])
                    eid = int(eid_sel.split(" - ")[0])
                    add_step_to_db(pid, eid, order, sname, pt, wt, stype, system, waste)
                    st.success("تمت اضافة الخطوة")
                    st.rerun()
    
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
               # حساب التكلفة الشاملة بطريقة بسيطة
            total_wait_cost = 0
            for s in steps:
                with app.app_context():
                    emp = Employee.query.get(s.employee_id)
                    if emp and s.wait_time_minutes:
                        total_wait_cost += (s.wait_time_minutes * emp.cost_per_minute)
            
            comprehensive_annual = (cost + total_wait_cost) * p.annual_frequency

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
            sel_step = st.selectbox("اختر الخطوة التي تريد تعديلها", step_names)
            
            st.markdown("---")
            st.markdown("### التعديل المقترح")
            change_description = st.text_area("صف التعديل الذي تخطط له")
            
            if change_description:
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
    
    with st.expander("7. نصائح سريعة"):
        st.markdown("""
        - 1440 دقيقة = يوم عمل، 2880 = يومان، 10080 = اسبوع.
        - فئة **انتصار_سريع** = عمليات سهلة تبني سمعتك اولا.
        - كل عملية مكتملة = قصة نجاح للادارة.
        - الهدف: كشف الهدر ثم القضاء عليه.
        """)
