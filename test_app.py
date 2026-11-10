"""用 Streamlit 官方 AppTest 跑一遍完整脚本，确认没有异常。"""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=180)
at.run()
print("首次渲染 exception:", at.exception)
print("info:", [i.value for i in at.info])

btn = next(b for b in at.button if "加载" in b.label)
btn.click().run()
print("点击加载后 exception:", at.exception)
print("error:", [e.value for e in at.error])
print("warning:", [w.value for w in at.warning])
print("tabs:", [t.label for t in at.tabs])
print("metrics:", len(at.metric), [m.label for m in at.metric][:8])
print("subheaders:", [s.value for s in at.subheader])
