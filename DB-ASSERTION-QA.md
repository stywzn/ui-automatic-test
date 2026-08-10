# 数据库断言 Q&A（UI 自动化项目）

> 本项目 SUT 用 SQLite,专门为了能演示数据库断言。相关代码:`ui-tests/conftest.py` 的 `db` fixture + `tests/test_db.py`。

## Q1. 什么是数据库断言?为什么要做?
一个操作做完后,**不只信 UI 显示对、接口返回对,还直连数据库查一下,确认数据真的正确落库了**。
**为什么"响应对 ≠ 数据对"**:接口可能返回 200/成功,但实际:没写库、写错字段、写了脏数据、事务没提交……只有查库才能兜底。这是**三层校验**:UI(用户看到的)+ 接口(返回值)+ 数据库(真实落库)。

## Q2. 你怎么实现的?
```python
# conftest.py:直连 SQLite 的 fixture
@pytest.fixture
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # 按列名取值,像 dict
    yield conn
    conn.close()

# test_db.py:UI 建项后查库校验
def test_add_item_persisted(logged_in_page, db):
    dashboard = DashboardPage(logged_in_page)
    dashboard.add_item("落库检查项")
    expect(dashboard.items()).to_have_count(4)          # 先等 UI 更新(确保写入提交)
    row = db.execute("SELECT * FROM items WHERE title=?", ("落库检查项",)).fetchone()
    assert row is not None                               # 记录存在
    assert row["status"] == "open"                       # 字段正确
```

## Q3. 有什么坑?
- **竞态**:UI 点完"添加"接口可能还在飞。所以**先 `expect(...).to_have_count` 等 UI 更新**(说明写入已提交),再查库,否则可能查早了。
- **SQL 注入习惯**:用 `?` 参数化,绝不字符串拼接。
- **数据清理/隔离**:每条用例前 `autouse` fixture 调 `/api/reset` 重置库,保证从固定初始态开始,查询结果可预期。
- **cursor vs 简写**:`conn.execute(...).fetchone()` 是 sqlite 简写(内部隐式建 cursor);标准 DB-API 写法是 `cur=conn.cursor(); cur.execute(...); cur.fetchone()`,换 MySQL/PG 通用。

## Q4. 什么时候"没有"数据库断言?
被测系统**无状态**时(如纯 API 网关只转发、不落库),就没有数据库层可断言——那时校验重点在响应/契约/行为。所以做不做数据库断言**取决于 SUT 有没有持久层**。(对比:我另一个 API 网关项目就是无状态的,没有数据库断言。)

## 30 秒话术
> "我在 UI 操作之外加了数据库断言——直连 SQLite,新建工作项后查库确认真落库、字段对。因为接口返回成功不等于数据存对了,查库能兜住'假成功'。这样是 UI+接口+数据库三层校验,比只看 UI 可靠。"
