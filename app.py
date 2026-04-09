import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# ================= 页面全局配置 =================
st.set_page_config(
    page_title="医药靶点数据库系统",
    page_icon="💊",
    layout="wide"
)

# ================= 1. 数据库连接设置 =================
DB_USER = 'root'
DB_PASSWORD = '123123'
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'ttd_drug_target_db'


@st.cache_resource
def init_connection():
    engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4')
    return engine


engine = init_connection()


def format_in_clause(id_list):
    if not id_list: return "('')"
    if len(id_list) == 1: return f"('{id_list[0]}')"
    return str(tuple(id_list))


# ================= 2. 侧边栏导航与开发团队署名 =================
st.sidebar.title("💊 医药数据库")
st.sidebar.markdown("---")

menu = st.sidebar.radio("请选择核心功能",
                        [
                            "🏠 系统首页 (Dashboard)",
                            "🔍 疾病找药查靶点",
                            "🔬 靶点反查相关药物",
                            "💊 药物全景详情查询",
                            "🧪 多条件联合管线筛选",
                            "📊 行业数据统计图表"
                        ]
                        )

st.sidebar.markdown("---")

# 【已修改】去掉了伊拉木江前面的星号
team_card_html = """
<div style="background-color: #f4f6f9; padding: 15px; border-radius: 8px; margin-top: 10px; border-left: 5px solid #1E88E5; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
    <p style="color: #666; font-size: 13px; margin-bottom: 8px; text-align: center;">👨‍💻 <strong>项目开发团队</strong></p>
    <p style="color: #2C3E50; font-size: 15px; font-weight: bold; margin: 0; text-align: center; line-height: 1.6;">
        张朝 <br>
        伊拉木江•依明 <br>
        金轩石
    </p>
</div>
"""
st.sidebar.markdown(team_card_html, unsafe_allow_html=True)

# ================= 页面 1：系统首页 =================
if menu == "🏠 系统首页 (Dashboard)":
    st.title("欢迎使用 药物-靶点-疾病 数据检索平台")
    st.markdown("本系统核心数据构建于海量医药研发记录之上，支持多维度的数据关联挖掘与可视化检索。")

    st.subheader("数据库当前规模")
    col1, col2, col3, col4 = st.columns(4)
    with engine.connect() as conn:
        drug_cnt = pd.read_sql("SELECT COUNT(*) as c FROM ttd_drug_base", conn).iloc[0]['c']
        target_cnt = pd.read_sql("SELECT COUNT(*) as c FROM ttd_target_base", conn).iloc[0]['c']
        disease_cnt = pd.read_sql("SELECT COUNT(*) as c FROM ttd_disease_dict", conn).iloc[0]['c']
        relation_cnt = pd.read_sql("SELECT COUNT(*) as c FROM ttd_drug_disease_relation", conn).iloc[0]['c']

    col1.metric("入库药物总数", f"{drug_cnt:,} 个")
    col2.metric("收录靶点总数", f"{target_cnt:,} 个")
    col3.metric("疾病字典总数", f"{disease_cnt:,} 种")
    col4.metric("疾病-药物关联数", f"{relation_cnt:,} 条")

    st.markdown("---")
    st.info("👈 请点击左侧导航栏体验核心功能。")

# ================= 页面 2：疾病 -> 药物 -> 靶点 =================
elif menu == "🔍 疾病找药查靶点":
    st.header("基于疾病寻药寻靶点 (Disease ➔ Drug ➔ Target)")

    disease_input = st.text_input("请输入疾病名称 (例如: Non-small-cell lung cancer, Pruritus)")

    if st.button("🔍 开始查询该疾病", type="primary"):
        if disease_input:
            sql_drug = f"""
                SELECT ttd_drug_id, drug_name, disease_name, icd11_code, clinical_status 
                FROM ttd_drug_disease_relation 
                WHERE disease_name LIKE '%%{disease_input}%%'
            """
            df_drugs = pd.read_sql(sql_drug, engine)

            if not df_drugs.empty:
                st.success(f"✅ 找到了针对关键字 '{disease_input}' 的 {len(df_drugs)} 条药物研发记录！")
                st.dataframe(df_drugs, use_container_width=True)

                drug_ids = df_drugs['ttd_drug_id'].unique().tolist()
                id_str = format_in_clause(drug_ids)

                sql_target = f"""
                    SELECT t.ttd_target_id, t.target_name, t.gene_name, m.MOA 
                    FROM ttd_target_base t
                    JOIN drug_target_mapping m ON t.ttd_target_id = m.TargetID
                    WHERE m.DrugID IN {id_str}
                """
                df_targets = pd.read_sql(sql_target, engine)

                st.subheader("🧬 涉及的相关靶点与致病基因")
                if not df_targets.empty:
                    df_targets = df_targets.drop_duplicates()
                    st.dataframe(df_targets, use_container_width=True)
                else:
                    st.warning("该类药物暂无明确的靶点映射数据。")
            else:
                st.error("未找到相关记录，请尝试其他疾病英文名称。")

# ================= 页面 3：靶点 -> 药物 -> 疾病 =================
elif menu == "🔬 靶点反查相关药物":
    st.header("基于靶点反查药物与适应症 (Target ➔ Drug ➔ Disease)")

    target_input = st.text_input("请输入靶点名称或基因名 (例如: EGFR, Kinase, FGFR1)")

    if st.button("🧬 开始检索靶点", type="primary"):
        if target_input:
            sql_target = f"""
                SELECT ttd_target_id, target_name, gene_name, target_function, bio_class 
                FROM ttd_target_base 
                WHERE target_name LIKE '%%{target_input}%%' 
                   OR gene_name LIKE '%%{target_input}%%'
                LIMIT 50
            """
            df_targets = pd.read_sql(sql_target, engine)

            if not df_targets.empty:
                st.success(f"✅ 匹配到 {len(df_targets)} 个相关靶点：")
                st.dataframe(df_targets, use_container_width=True)

                target_ids = df_targets['ttd_target_id'].unique().tolist()
                t_id_str = format_in_clause(target_ids)

                sql_drugs = f"""
                    SELECT d.ttd_drug_id, d.trade_name AS drug_name, d.company, d.highest_status, m.MOA
                    FROM drug_target_mapping m
                    JOIN ttd_drug_base d ON m.DrugID = d.ttd_drug_id
                    WHERE m.TargetID IN {t_id_str}
                """
                df_drugs = pd.read_sql(sql_drugs, engine)

                st.subheader("💊 靶向以上靶点的药物清单")
                if not df_drugs.empty:
                    st.dataframe(df_drugs.drop_duplicates(), use_container_width=True)
                else:
                    st.warning("尚未收录针对这些靶点的药物。")
            else:
                st.error("未找到相关靶点记录。")

# ================= 页面 4：药物 -> 靶点 + 疾病 =================
elif menu == "💊 药物全景详情查询":
    st.header("药物全景信息查询 (Drug ➔ Target & Disease)")

    drug_input = st.text_input("请输入药物名称 (例如: Ibrance)")

    if st.button("💊 开始查询药物", type="primary"):
        if drug_input:
            sql_drug = f"""
                SELECT ttd_drug_id, trade_name AS drug_name, company, therapeutic_class, drug_type, highest_status
                FROM ttd_drug_base 
                WHERE trade_name LIKE '%%{drug_input}%%'
            """
            df_drugs = pd.read_sql(sql_drug, engine)

            if not df_drugs.empty:
                st.success("✅ 找到如下药物基础信息：")
                st.dataframe(df_drugs, use_container_width=True)

                drug_ids = df_drugs['ttd_drug_id'].unique().tolist()
                d_id_str = format_in_clause(drug_ids)

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("🎯 作用靶点 (Targets)")
                    sql_t = f"""
                        SELECT t.target_name, m.MOA 
                        FROM drug_target_mapping m
                        JOIN ttd_target_base t ON m.TargetID = t.ttd_target_id
                        WHERE m.DrugID IN {d_id_str}
                    """
                    df_t = pd.read_sql(sql_t, engine)
                    if not df_t.empty:
                        st.dataframe(df_t, use_container_width=True)
                    else:
                        st.info("无靶点记录")

                with col2:
                    st.subheader("🦠 适应症 (Diseases)")
                    sql_d = f"""
                        SELECT disease_name, clinical_status 
                        FROM ttd_drug_disease_relation 
                        WHERE ttd_drug_id IN {d_id_str}
                    """
                    df_d = pd.read_sql(sql_d, engine)
                    if not df_d.empty:
                        st.dataframe(df_d, use_container_width=True)
                    else:
                        st.info("无适应症记录")
            else:
                st.error("未找到相关药物，请核对名称。")

# ================= 页面 5：(新增功能) 联合管线筛选 =================
elif menu == "🧪 多条件联合管线筛选":
    st.header("新药研发管线数据挖掘")


    with engine.connect() as conn:
        status_opts = \
        pd.read_sql("SELECT DISTINCT highest_status FROM ttd_drug_base WHERE highest_status IS NOT NULL", conn)[
            'highest_status'].tolist()
        class_opts = \
        pd.read_sql("SELECT DISTINCT therapeutic_class FROM ttd_drug_base WHERE therapeutic_class IS NOT NULL", conn)[
            'therapeutic_class'].dropna().unique().tolist()

    c1, c2 = st.columns(2)
    with c1:
        sel_status = st.selectbox("1. 选择临床研发状态 (Highest Status)", ["全部"] + status_opts)
    with c2:
        sel_class = st.selectbox("2. 选择治疗类别 (Therapeutic Class)", ["全部"] + class_opts[:100])

    if st.button("🚀 执行多维度筛选", type="primary"):
        conditions = []
        if sel_status != "全部":
            conditions.append(f"highest_status = '{sel_status}'")
        if sel_class != "全部":
            conditions.append(f"therapeutic_class = '{sel_class}'")

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        sql_filter = f"""
            SELECT ttd_drug_id, trade_name AS drug_name, company, therapeutic_class, highest_status 
            FROM ttd_drug_base 
            {where_clause}
            LIMIT 500
        """

        df_filtered = pd.read_sql(sql_filter, engine)

        if not df_filtered.empty:
            st.success(f"✅ 成功筛选出 {len(df_filtered)} 款符合要求的药物 (最多展示500条)：")
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.warning("没有找到符合该组合条件的药物，请更换筛选条件。")


# ================= 页面 6：数据图表与宏观分析 =================
# ================= 页面 6：数据图表与宏观分析 (更新版) =================
elif menu == "📊 行业数据统计图表":
    st.header("宏观数据分析与可视化")
    st.markdown("请点击下方的选项卡，选择查看对应维度的统计数据：")

    # 创建 5 个选项卡
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🦠 疾病药物关联排行",
        "📈 靶点分类分布",
        "🏭 药企管线排名",
        "🧪 药物机制 (MOA)",
        "📊 综合概览"
    ])

    # 1. 新增功能：一疾病拥有的药物最多 Top 10
    with tab1:
        st.subheader("拥有最多药物研发的疾病 (Top 10)")
        sql_disease = """
            SELECT disease_name, COUNT(*) as drug_count 
            FROM ttd_drug_disease_relation 
            GROUP BY disease_name 
            ORDER BY drug_count DESC 
            LIMIT 10
        """
        df_disease = pd.read_sql(sql_disease, engine).set_index('disease_name')
        st.bar_chart(df_disease)

    # 2. 靶点分类
    with tab2:
        st.subheader("靶点生物学分类占比 (Top 10)")
        sql_bio = """
            SELECT bio_class, COUNT(*) as count 
            FROM ttd_target_base 
            WHERE bio_class IS NOT NULL AND bio_class != ''
            GROUP BY bio_class 
            ORDER BY count DESC LIMIT 10
        """
        df_bio = pd.read_sql(sql_bio, engine).set_index('bio_class')
        st.bar_chart(df_bio)

    # 3. 药企排名
    with tab3:
        st.subheader("拥有最多管线的制药企业 (Top 10)")
        sql_comp = """
            SELECT company, COUNT(*) as drug_count 
            FROM ttd_drug_base 
            WHERE company IS NOT NULL AND company != ''
            GROUP BY company 
            ORDER BY drug_count DESC LIMIT 10
        """
        df_comp = pd.read_sql(sql_comp, engine).set_index('company')
        st.bar_chart(df_comp)

    # 4. 药物作用机制
    with tab4:
        st.subheader("药物作用机制 (MOA) 分布情况")
        sql_moa = """
            SELECT MOA, COUNT(*) as count 
            FROM drug_target_mapping 
            WHERE MOA IS NOT NULL AND MOA != '.'
            GROUP BY MOA 
            ORDER BY count DESC LIMIT 15
        """
        df_moa = pd.read_sql(sql_moa, engine).set_index('MOA')
        st.area_chart(df_moa)

    # 5. 综合概览
    with tab5:
        st.subheader("全维度指标概览")
        # 将上述所有查询结果进行横向对比
        st.info("此标签页展示当前系统数据分布的综合概览，方便进行多维度比对。")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("疾病覆盖Top 5")
            st.bar_chart(pd.read_sql(
                "SELECT disease_name, COUNT(*) as c FROM ttd_drug_disease_relation GROUP BY disease_name ORDER BY c DESC LIMIT 5",
                engine).set_index('disease_name'))
        with col_b:
            st.write("药企活跃Top 5")
            st.bar_chart(pd.read_sql(
                "SELECT company, COUNT(*) as c FROM ttd_drug_base WHERE company != '' GROUP BY company ORDER BY c DESC LIMIT 5",
                engine).set_index('company'))