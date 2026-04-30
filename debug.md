User@Law MINGW64 ~/Desktop/team5pm-streamlit-app (onboarding)
$ streamlit run streamlit_app.py

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.0.208:8501

C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:83: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_clients = pd.read_sql(query, conn, params=(user_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:100: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_brands = pd.read_sql(query, conn, params=(organization_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:182: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn, params=(organization_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:249: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn, params=params)
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:83: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_clients = pd.read_sql(query, conn, params=(user_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:100: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_brands = pd.read_sql(query, conn, params=(organization_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:182: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn, params=(organization_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:249: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn, params=params)
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:83: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_clients = pd.read_sql(query, conn, params=(user_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:100: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_brands = pd.read_sql(query, conn, params=(organization_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:182: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn, params=(organization_id,))
2026-04-30 11:40:32.696 Uncaught app execution
Traceback (most recent call last):
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\runtime\scriptrunner\exec_code.py", line 129, in exec_func_with_error_handling
    result = func()
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\runtime\scriptrunner\script_runner.py", line 689, in code_to_exec
    exec(code, module.__dict__)  # noqa: S102
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\User\Desktop\team5pm-streamlit-app\streamlit_app.py", line 484, in <module>
    if r_cols[5].button("🔄", key=f"sync_{b_id}_{plat}_{row['platform_account_id']}"):
       ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\runtime\metrics_util.py", line 563, in wrapped_func
    result = non_optional_func(*args, **kwargs)
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\elements\widgets\button.py", line 379, in button
    return self.dg._button(
           ~~~~~~~~~~~~~~~^
        label,
        ^^^^^^
    ...<12 lines>...
        shortcut=shortcut,
        ^^^^^^^^^^^^^^^^^^
    )
    ^
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\elements\widgets\button.py", line 1648, in _button
    element_id = compute_and_register_element_id(
        "form_submit_button" if is_form_submitter else "button",
    ...<10 lines>...
        shortcut=normalized_shortcut,
    )
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\elements\lib\utils.py", line 265, in compute_and_register_element_id
    _register_element_id(ctx, element_type, element_id)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\elements\lib\utils.py", line 145, in _register_element_id
    raise StreamlitDuplicateElementKey(user_key)
streamlit.errors.StreamlitDuplicateElementKey: There are multiple elements with the same `key='sync_ali_abdaal_youtube_UCoOae5nYA7VqaXzerajD0lg'`. To fix this, please make sure that the `key` argument is unique for each element you create.
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:83: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_clients = pd.read_sql(query, conn, params=(user_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:100: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_brands = pd.read_sql(query, conn, params=(organization_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:182: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn, params=(organization_id,))
🔍 Looking for .env at: C:\Users\User\Desktop\team5pm-streamlit-app\.env
📡 Loaded Snowflake Account: FISTFNF-AIB47082
C:\Users\User\Desktop\team5pm-streamlit-app\ingestion\config_loader.py:28: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn)
⚠️ No youtube records fetched. Skipping.
🏗️  Executing Snowflake Stored Procedure: SP_BUILD_CANONICAL_PERFORMANCE...
✅ SUCCESS: SILVER TABLE REBUILT WITH CLIENT_ID

🧠 New data detected in Silver layer. Triggering automatic model retraining...
Fetching Silver data for training...
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:249: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn, params=params)
❌ Not enough data to train any model. Ingest more videos first.
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:83: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_clients = pd.read_sql(query, conn, params=(user_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:100: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df_brands = pd.read_sql(query, conn, params=(organization_id,))
C:\Users\User\Desktop\team5pm-streamlit-app\utils\data_loader.py:182: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
  df = pd.read_sql(query, conn, params=(organization_id,))
2026-04-30 11:41:42.050 Uncaught app execution
Traceback (most recent call last):
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\runtime\scriptrunner\exec_code.py", line 129, in exec_func_with_error_handling
    result = func()
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\runtime\scriptrunner\script_runner.py", line 689, in code_to_exec
    exec(code, module.__dict__)  # noqa: S102
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\User\Desktop\team5pm-streamlit-app\streamlit_app.py", line 484, in <module>
    if r_cols[5].button("🔄", key=f"sync_{b_id}_{plat}_{row['platform_account_id']}"):
       ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\runtime\metrics_util.py", line 563, in wrapped_func
    result = non_optional_func(*args, **kwargs)
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\elements\widgets\button.py", line 379, in button
    return self.dg._button(
           ~~~~~~~~~~~~~~~^
        label,
        ^^^^^^
    ...<12 lines>...
        shortcut=shortcut,
        ^^^^^^^^^^^^^^^^^^
    )
    ^
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\elements\widgets\button.py", line 1648, in _button
    element_id = compute_and_register_element_id(
        "form_submit_button" if is_form_submitter else "button",
    ...<10 lines>...
        shortcut=normalized_shortcut,
    )
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\elements\lib\utils.py", line 265, in compute_and_register_element_id
    _register_element_id(ctx, element_type, element_id)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\User\Desktop\team5pm-streamlit-app\.venv\Lib\site-packages\streamlit\elements\lib\utils.py", line 145, in _register_element_id
    raise StreamlitDuplicateElementKey(user_key)
streamlit.errors.StreamlitDuplicateElementKey: There are multiple elements with the same `key='sync_ali_abdaal_youtube_UCoOae5nYA7VqaXzerajD0lg'`. To fix this, please make sure that the `key` argument is unique for each element you create.