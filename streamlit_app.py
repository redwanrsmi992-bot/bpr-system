import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from flask import Flask
from models import db, Employee, Process, Step

# ---- إعداد التطبيق ----
st.set_page_config(page_title="نظام إعادة هندسة العمليات", layout="wide")
st.title("🔍 نظام إعادة هندسة العمليات - دائرة الموازنة العامة")

# ---- إعداد قاعدة البيانات ----
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
menu = st.sidebar.radio("📌 القائمة", [
    "الرئيسية",
    "إضافة موظف",
    "إضافة عملية",
    "إضافة خطوات",
    "لوحة التحكم",
    "📖 دليل الاستخدام"
])

# ================== الصفحة الرئيسية ==================
if menu == "الرئيسية":
    st.subheader("📋 قائمة العمليات")
    processes = get_processes()
    if processes:
        for p in processes:
            with app.app_context():
                eff = Process.query.get(p.id).flow_efficiency
                cost = Process.query.get(p.id).annual_cost
            with st.expander(f"{p.id} - {p.name} ({p.category})"):
                col1, col2, col3 = st.columns(3)
                col1.metric("كفاءة التدفق", f"{eff:.2f}%")
                col2.metric("التكلفة السنوية", f"{cost:,.2f} د.أ")
                col3.metric("التكرار السنوي", p.annual_frequency)
                
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("✏️ تعديل", key=f"edit_{p.id}"):
                        st.session_state[f"editing_{p.id}"] = True
                with col_del:
                    if st.button("🗑️ حذف", key=f"del_{p.id}"):
                        delete_process_from_db(p.id)
                        st.success("تم الحذف!")
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
                            if st.form_submit_button("💾 حفظ التعديلات"):
                                update_process_in_db(p.id, new_name, new_cat, new_freq, new_status)
                                st.session_state[f"editing_{p.id}"] = False
                                st.success("تم التعديل!")
                                st.rerun()
                        with col_cancel:
                            if st.form_submit_button("❌ إلغاء"):
                                st.session_state[f"editing_{p.id}"] = False
                                st.rerun()
    else:
        st.info("لا توجد عمليات بعد. أضف عملية من القائمة الجانبية.")

# ================== إضافة موظف ==================
elif menu == "إضافة موظف":
    st.subheader("👤 إدارة الموظفين")
    
    with st.expander("➕ إضافة موظف جديد", expanded=False):
        with st.form("add_emp"):
            title = st.text_input("المسمى الوظيفي")
            st.markdown("**نطاق الراتب الشهري (دينار أردني)**")
            min_salary, max_salary = st.slider(
                "اختر نطاق الراتب (من - إلى)",
                min_value=300, max_value=5000, value=(500, 1000), step=50
            )
            avg_salary = (min_salary + max_salary) // 2
            st.info(f"💰 الراتب المعتمد للحساب: **{avg_salary} دينار** (متوسط النطاق)")
            if st.form_submit_button("حفظ"):
                if title:
                    add_employee_to_db(title, float(avg_salary))
                    st.success(f"تمت إضافة الموظف: {title}")
                    st.rerun()
                else:
                    st.error("الرجاء إدخال المسمى الوظيفي")
    
    emps = get_employees()
    if emps:
        st.subheader("📋 الموظفون الحاليون")
        for e in emps:
            with st.expander(f"{e.id} - {e.title} ({e.monthly_cost:.0f} د.أ)"):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ تعديل", key=f"edit_emp_{e.id}"):
                        st.session_state[f"editing_emp_{e.id}"] = True
                with col2:
                    if st.button("🗑️ حذف", key=f"del_emp_{e.id}"):
                        delete_employee_from_db(e.id)
                        st.success("تم الحذف!")
                        st.rerun()
                
                if st.session_state.get(f"editing_emp_{e.id}", False):
                    with st.form(f"edit_emp_form_{e.id}"):
                        new_title = st.text_input("المسمى الوظيفي", value=e.title)
                        new_cost = st.number_input("الراتب الشهري", min_value=100, value=int(e.monthly_cost))
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 حفظ"):
                                update_employee_in_db(e.id, new_title, float(new_cost))
                                st.session_state[f"editing_emp_{e.id}"] = False
                                st.success("تم التعديل!")
                                st.rerun()
                        with col_cancel:
                            if st.form_submit_button("❌ إلغاء"):
                                st.session_state[f"editing_emp_{e.id}"] = False
                                st.rerun()
    else:
        st.info("لا يوجد موظفين بعد.")

# ================== إضافة عملية ==================
elif menu == "إضافة عملية":
    st.subheader("➕ إضافة عملية جديدة")
    with st.form("add_proc"):
        name = st.text_input("اسم العملية")
        category = st.selectbox("الفئة", ["استراتيجية", "انتصار_سريع", "روتينية", "للدراسة"])
        freq = st.number_input("التكرار السنوي", min_value=1, value=1)
        status = st.selectbox("الحالة", ["غير_مبدوء", "تحت_الدراسة", "مكتمل"])
        if st.form_submit_button("حفظ"):
            if name:
                add_process_to_db(name, category, freq, status)
                st.success(f"تمت إضافة العملية: {name}")
                st.rerun()
            else:
                st.error("الرجاء إدخال اسم العملية")

# ================== إضافة خطوات ==================
elif menu == "إضافة خطوات":
    st.subheader("📝 إضافة خطوات لعملية")
    processes = get_processes()
    employees = get_employees()
    if not processes:
        st.warning("لا توجد عمليات. أضف عملية أولاً.")
    elif not employees:
        st.warning("لا توجد موظفين. أضف موظفاً أولاً.")
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
            waste = st.text_input("فئة الهدر (إن وجدت)")
            if st.form_submit_button("حفظ"):
                pid = int(pid_sel.split(" - ")[0])
                eid = int(eid_sel.split(" - ")[0])
                add_step_to_db(pid, eid, order, sname, pt, wt, stype, system, waste)
                st.success("تمت إضافة الخطوة!")
                st.rerun()

# ================== لوحة التحكم ==================
elif menu == "لوحة التحكم":
    st.subheader("📊 لوحة التحكم")
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
            c1, c2, c3 = st.columns(3)
            c1.metric("كفاءة التدفق", f"{eff:.2f}%")
            c2.metric("زمن الدورة (ساعة)", f"{lead/60:.1f}")
            c3.metric("التكلفة السنوية", f"{cost:,.2f} د.أ")
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
            st.info("لا توجد خطوات لهذه العملية. أضف خطوات من القائمة الجانبية.")
    else:
        st.info("لا توجد عمليات بعد.")

# ================== دليل الاستخدام ==================
elif menu == "📖 دليل الاستخدام":
    st.subheader("📖 دليل استخدام نظام إعادة هندسة العمليات")
    
    with st.expander("🏠 1. الرئيسية", expanded=True):
        st.markdown("""
        **ماذا ترى؟** قائمة بجميع العمليات في صناديق قابلة للطي.
        - كل صندوق يعرض: كفاءة التدفق، التكلفة السنوية، التكرار السنوي.
        - **✏️ تعديل:** لتغيير اسم العملية، الفئة، التكرار، أو الحالة.
        - **🗑️ حذف:** لحذف العملية نهائياً.
        """)
    
    with st.expander("👤 2. إدارة الموظفين"):
        st.markdown("""
        **إضافة موظف جديد:**
        - اكتب المسمى الوظيفي.
        - اختر نطاق الراتب من شريط التمرير.
        - يحسب التطبيق المتوسط تلقائياً ويستخدمه في حسابات التكلفة.
        
        **تعديل/حذف موظف:**
        - اضغط ✏️ لتغيير المسمى أو الراتب.
        - اضغط 🗑️ لحذف الموظف.
        """)
    
    with st.expander("➕ 3. إضافة عملية"):
        st.markdown("""
        | الحقل | الوصف |
        |-------|-------|
        | اسم العملية | مثل: "المناقلات المالية" |
        | الفئة | استراتيجية، انتصار_سريع، روتينية، للدراسة |
        | التكرار السنوي | كم مرة تحدث في السنة |
        | الحالة | غير_مبدوء، تحت_الدراسة، مكتمل |
        """)
    
    with st.expander("📝 4. إضافة خطوات"):
        st.markdown("""
        | الحقل | الوصف | مثال |
        |-------|-------|------|
        | العملية | اختر العملية المستهدفة | المناقلات المالية |
        | الموظف | من يقوم بهذه الخطوة | مدقق مالي |
        | رقم الترتيب | تسلسل الخطوة | 1, 2, 3... |
        | اسم الخطوة | وصف مختصر | "انتظار توقيع المدير" |
        | وقت المعالجة | دقائق العمل الفعلي | 5 |
        | وقت الانتظار | دقائق الانتظار | 1440 (يوم كامل) |
        | نوع الخطوة | VA = قيمة، BNVA = ضرورية، NVA = هدر |
        | النظام | Oracle, GFMIS, ورقي, Outlook... |
        | فئة الهدر | للخطوات NVA فقط | انتظار، موافقات_زائدة |
        """)
    
    with st.expander("📊 5. لوحة التحكم"):
        st.markdown("""
        اختر عملية لتشاهد:
        - **3 بطاقات:** كفاءة التدفق، زمن الدورة، التكلفة السنوية.
        - **الرسم الشريطي:** أخضر = وقت عمل، أحمر = وقت انتظار.
        - **الرسم الدائري:** العمل المفيد مقابل الهدر.
        - **جدول تفصيلي** لجميع الخطوات.
        """)
    
    with st.expander("📈 6. كيف تقرأ النتائج؟"):
        st.markdown("""
        | كفاءة التدفق | التقييم | الإجراء |
        |-------------|--------|---------|
        | أقل من 5% | 🔴 كارثة | تدخل فوري |
        | 5% - 20% | 🟠 سيء جداً | أولوية للتحسين |
        | 20% - 40% | 🟡 مقبول | مجال للتحسين |
        | 40% - 60% | 🟢 جيد | تحسينات طفيفة |
        | أكثر من 60% | 🔵 ممتاز | حافظ على المستوى |
        """)
    
    with st.expander("💡 7. نصائح سريعة"):
        st.markdown("""
        - ⏱️ 1440 دقيقة = يوم عمل، 2880 = يومان، 10080 = أسبوع.
        - 🚀 فئة **انتصار_سريع** = عمليات سهلة تبني سمعتك أولاً.
        - 📊 كل عملية مكتملة = قصة نجاح للإدارة.
        - 🎯 الهدف: كشف الهدر ثم القضاء عليه.
        """)
