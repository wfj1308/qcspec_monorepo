-- ============================================================
-- QCSpec · Supabase 数据库结构
-- Version Control for the Physical World
-- v://cn.中北/ · GitPeg · 2026
--
-- 执行顺序：
--   1. 启用扩展
--   2. 枚举类型
--   3. 核心表
--   4. 索引
--   5. Row Level Security (RLS)
--   6. 触发器
--   7. 函数
--   8. 初始数据
-- ============================================================

-- ────────────────────────────────────────
-- 1. 扩展
-- ────────────────────────────────────────
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ────────────────────────────────────────
-- 2. 枚举类型
-- ────────────────────────────────────────

-- DTORole 六层权限（对应 GitPeg 协议）
create type dto_role as enum (
  'PUBLIC',        -- 公开可查
  'MARKET',        -- 商业交互
  'AI',            -- 执行器/质检员
  'SUPERVISOR',    -- 监理/项目经理
  'OWNER',         -- 管理员/业主
  'REGULATOR'      -- 监管机构
);

-- 节点类型
create type node_type as enum (
  'Enterprise',    -- 企业根节点
  'Project',       -- 项目节点
  'Segment',       -- 标段/路段节点
  'Report',        -- 质检报告节点
  'Photo',         -- 照片节点
  'Device'         -- 设备节点
);

-- 质检结果
create type inspect_result as enum (
  'pass',          -- 合格
  'warn',          -- 观察
  'fail'           -- 不合格
);

-- 项目状态
create type project_status as enum (
  'pending',       -- 待开始
  'active',        -- 进行中
  'closed'         -- 已完成
);

-- Proof 状态
create type proof_status as enum (
  'pending',       -- 待确认
  'confirmed',     -- 已确认
  'sealed'         -- 已Seal
);

-- Seal 状态
create type seal_status as enum (
  'unsigned',      -- 未签署
  'partial',       -- 部分签署
  'sealed'         -- 全部签署完成
);

-- ────────────────────────────────────────
-- 3. 核心表
-- ────────────────────────────────────────

-- ══ 3.1 企业（租户根节点）══
create table enterprises (
  id             uuid primary key default uuid_generate_v4(),
  v_uri          text not null unique,        -- v://cn.企业名/
  name           text not null,               -- 企业全称
  short_name     text,                        -- 简称
  credit_code    text,                        -- 统一社会信用代码
  domain         text,                        -- 企业域名（用于域名翻牌）
  industry       text,                        -- 行业类型
  plan           text default 'basic',        -- basic / pro / enterprise
  node_status    text default 'active',       -- active / suspended
  proof_quota    int  default 500,            -- 年度Proof配额
  proof_used     int  default 0,              -- 已用Proof次数
  created_at     timestamptz default now(),
  updated_at     timestamptz default now()
);

-- ══ 3.2 用户（executor 节点）══
create table users (
  id             uuid primary key default uuid_generate_v4(),
  enterprise_id  uuid references enterprises(id) on delete cascade,
  v_uri          text not null unique,        -- v://cn.企业/executor/姓名/
  name           text not null,
  phone          text,
  email          text unique,
  password_hash  text,                        -- 生产用 Supabase Auth
  dto_role       dto_role default 'AI',       -- 全局角色
  title          text,                        -- 职务
  is_active      boolean default true,
  last_login     timestamptz,
  created_at     timestamptz default now()
);

-- ══ 3.3 项目（Project 节点）══
create table projects (
  id             uuid primary key default uuid_generate_v4(),
  enterprise_id  uuid references enterprises(id) on delete cascade,
  v_uri          text not null unique,        -- v://cn.企业/highway/项目名/
  name           text not null,
  type           text not null,               -- highway/bridge/road/tunnel...
  owner_unit     text not null,               -- 业主单位
  contractor     text,                        -- 施工单位
  supervisor     text,                        -- 监理单位
  contract_no    text,
  start_date     date,
  end_date       date,
  description    text,
  seg_type       text default 'km',           -- km/contract/structure
  seg_start      text,                        -- 起始桩号
  seg_end        text,                        -- 终止桩号
  status         project_status default 'active',
  perm_template  text default 'standard',     -- standard/strict/open/custom
  proof_count    int default 0,               -- 累计Proof数
  record_count   int default 0,               -- 累计质检记录数
  photo_count    int default 0,               -- 累计照片数
  created_by     uuid references users(id),
  created_at     timestamptz default now(),
  updated_at     timestamptz default now()
);

-- ══ 3.4 项目成员（权限绑定）══
create table project_members (
  id             uuid primary key default uuid_generate_v4(),
  project_id     uuid references projects(id) on delete cascade,
  user_id        uuid references users(id) on delete cascade,
  dto_role       dto_role not null,           -- 项目内角色（可与全局角色不同）
  invited_by     uuid references users(id),
  joined_at      timestamptz default now(),
  unique(project_id, user_id)
);

-- ══ 3.5 质检记录（核心数据）══
create table inspections (
  id             uuid primary key default uuid_generate_v4(),
  project_id     uuid references projects(id) on delete cascade,
  enterprise_id  uuid references enterprises(id),
  v_uri          text,                        -- v://cn.企业/project/XXX/inspection/ID/
  location       text not null,               -- 桩号，如 K50+200
  type           text not null,               -- flatness/crack/compaction...
  type_name      text,                        -- 中文名称
  value          numeric not null,            -- 实测值
  standard       numeric,                     -- 规范标准值
  unit           text default '',             -- 单位
  result         inspect_result not null,     -- pass/warn/fail
  person         text,                        -- 检测人员姓名
  person_id      uuid references users(id),
  remark         text,
  inspected_at   timestamptz default now(),

  -- v:// Proof 关联
  proof_id       text,                        -- GP-PROOF-XXXXXXXX
  proof_hash     text,                        -- SHA256哈希
  proof_status   proof_status default 'pending',

  -- Seal 关联
  seal_status    seal_status default 'unsigned',
  sealed_by      uuid references users(id),
  sealed_at      timestamptz,

  created_at     timestamptz default now()
);

-- ══ 3.6 照片（Photo 节点）══
create table photos (
  id             uuid primary key default uuid_generate_v4(),
  project_id     uuid references projects(id) on delete cascade,
  enterprise_id  uuid references enterprises(id),
  inspection_id  uuid references inspections(id) on delete set null,
  v_uri          text,                        -- v://cn.企业/project/XXX/photo/ID/
  file_name      text not null,
  storage_path   text not null,               -- Supabase Storage 路径
  storage_url    text,                        -- 公开访问URL
  location       text,                        -- 拍摄桩号
  gps_lat        numeric,                     -- GPS纬度
  gps_lng        numeric,                     -- GPS经度
  taken_at       timestamptz,                 -- 拍摄时间（EXIF）
  uploaded_by    uuid references users(id),
  file_size      int,                         -- 字节
  width          int,
  height         int,
  proof_id       text,                        -- 照片Proof
  proof_hash     text,
  created_at     timestamptz default now()
);

-- ══ 3.7 质检报告（Report 节点）══
create table reports (
  id             uuid primary key default uuid_generate_v4(),
  project_id     uuid references projects(id) on delete cascade,
  enterprise_id  uuid references enterprises(id),
  v_uri          text unique,                 -- v://cn.企业/project/XXX/reports/编号/
  report_no      text not null unique,        -- QC-20260322074348
  location       text,                        -- 检测范围
  inspection_ids uuid[],                      -- 关联质检记录ID列表
  photo_ids      uuid[],                      -- 关联照片ID列表

  -- 统计
  total_count    int default 0,
  pass_count     int default 0,
  warn_count     int default 0,
  fail_count     int default 0,
  pass_rate      numeric,                     -- 合格率%

  -- 内容
  conclusion     text,
  fail_items     text,
  suggestions    text,

  -- 文件
  file_path      text,                        -- 报告文件存储路径
  file_url       text,                        -- 下载URL
  template_used  text,                        -- 使用的模板

  -- v:// Proof
  proof_id       text,                        -- 报告Proof
  proof_hash     text,
  proof_status   proof_status default 'pending',

  -- Seal
  seal_status    seal_status default 'unsigned',
  seal_records   jsonb default '[]',          -- [{user_id, role, signed_at, hash}]

  -- 人员
  inspector_id   uuid references users(id),
  generated_by   uuid references users(id),

  generated_at   timestamptz default now(),
  created_at     timestamptz default now()
);

-- ══ 3.8 Proof 链（不可篡改的操作日志）══
create table proof_chain (
  id             uuid primary key default uuid_generate_v4(),
  proof_id       text not null unique,        -- GP-PROOF-XXXXXXXXXXXXXXXX
  proof_hash     text not null,               -- SHA256
  parent_hash    text,                        -- 前序Proof哈希（链式引用）

  -- 关联
  enterprise_id  uuid references enterprises(id),
  project_id     uuid references projects(id),
  v_uri          text not null,               -- 所属节点URI
  object_type    text not null,               -- inspection/report/photo/config
  object_id      uuid,                        -- 关联对象ID

  -- 操作信息
  action         text not null,               -- create/update/seal/generate
  actor_v_uri    text,                        -- 操作者v://地址
  actor_id       uuid references users(id),
  summary        text,                        -- 操作摘要
  payload_hash   text,                        -- 操作内容哈希

  -- 状态
  status         proof_status default 'confirmed',
  anchored_at    timestamptz,                 -- 上链时间（生产环境对接GitPeg）

  created_at     timestamptz default now()
);

-- ══ 3.9 v:// 节点注册表（全局）══
create table v_nodes (
  id             uuid primary key default uuid_generate_v4(),
  uri            text not null unique,        -- v:// 完整地址
  parent_uri     text,                        -- 父节点地址
  node_type      node_type not null,
  enterprise_id  uuid references enterprises(id),
  object_id      uuid,                        -- 关联业务对象ID
  object_table   text,                        -- 关联表名
  status         text default 'active',       -- active/suspended/archived
  peg_count      int default 0,               -- Peg提交次数
  last_peg_at    timestamptz,
  metadata       jsonb default '{}',          -- 扩展元数据
  created_at     timestamptz default now(),
  updated_at     timestamptz default now()
);

-- ══ 3.10 Seal 签署记录══
create table seals (
  id             uuid primary key default uuid_generate_v4(),
  object_type    text not null,               -- inspection/report
  object_id      uuid not null,
  v_uri          text,
  signer_id      uuid references users(id),
  signer_v_uri   text,
  signer_role    dto_role,
  proof_id       text,                        -- 签署事件Proof
  signature_hash text,                        -- 签署哈希
  comment        text,
  signed_at      timestamptz default now()
);

-- ══ 3.11 系统配置（每个企业一份）══
create table enterprise_configs (
  id               uuid primary key default uuid_generate_v4(),
  enterprise_id    uuid references enterprises(id) unique,
  -- 报告设置
  report_header    text,                      -- 报告抬头
  report_template  text default 'standard',   -- 模板名
  -- 通知设置
  notify_fail      boolean default true,
  notify_daily     boolean default true,
  notify_join      boolean default false,
  notify_proof     boolean default false,
  -- 集成设置
  gitpeg_enabled   boolean default false,     -- GitPeg Proof接入
  erp_enabled      boolean default false,     -- ERP同步
  wechat_enabled   boolean default true,      -- 微信小程序
  -- 自定义
  custom_fields    jsonb default '{}',
  updated_at       timestamptz default now()
);

-- ────────────────────────────────────────
-- 4. 索引（查询性能）
-- ────────────────────────────────────────

-- 企业
create index idx_enterprises_v_uri    on enterprises(v_uri);
create index idx_enterprises_domain   on enterprises(domain);

-- 用户
create index idx_users_enterprise     on users(enterprise_id);
create index idx_users_v_uri          on users(v_uri);
create index idx_users_email          on users(email);

-- 项目
create index idx_projects_enterprise  on projects(enterprise_id);
create index idx_projects_v_uri       on projects(v_uri);
create index idx_projects_status      on projects(status);
create index idx_projects_type        on projects(type);

-- 质检记录
create index idx_inspections_project  on inspections(project_id);
create index idx_inspections_result   on inspections(result);
create index idx_inspections_location on inspections(location);
create index idx_inspections_type     on inspections(type);
create index idx_inspections_at       on inspections(inspected_at desc);
create index idx_inspections_proof    on inspections(proof_id);

-- 照片
create index idx_photos_project       on photos(project_id);
create index idx_photos_inspection    on photos(inspection_id);
create index idx_photos_location      on photos(location);

-- 报告
create index idx_reports_project      on reports(project_id);
create index idx_reports_v_uri        on reports(v_uri);
create index idx_reports_no           on reports(report_no);
create index idx_reports_at           on reports(generated_at desc);

-- Proof链
create index idx_proof_v_uri          on proof_chain(v_uri);
create index idx_proof_object         on proof_chain(object_id);
create index idx_proof_project        on proof_chain(project_id);
create index idx_proof_created        on proof_chain(created_at desc);

-- v://节点
create index idx_v_nodes_uri          on v_nodes(uri);
create index idx_v_nodes_parent       on v_nodes(parent_uri);
create index idx_v_nodes_enterprise   on v_nodes(enterprise_id);

-- ────────────────────────────────────────
-- 5. Row Level Security（多租户隔离）
-- ────────────────────────────────────────

alter table enterprises        enable row level security;
alter table users              enable row level security;
alter table projects           enable row level security;
alter table project_members    enable row level security;
alter table inspections        enable row level security;
alter table photos             enable row level security;
alter table reports            enable row level security;
alter table proof_chain        enable row level security;
alter table v_nodes            enable row level security;
alter table seals              enable row level security;
alter table enterprise_configs enable row level security;

-- ── 辅助函数：获取当前用户所属企业 ──
create or replace function current_enterprise_id()
returns uuid language sql stable as $$
  select enterprise_id from users
  where id = auth.uid()
  limit 1;
$$;

-- ── 辅助函数：获取当前用户角色 ──
create or replace function current_user_role()
returns dto_role language sql stable as $$
  select dto_role from users
  where id = auth.uid()
  limit 1;
$$;

-- ── 辅助函数：当前用户是否有项目权限 ──
create or replace function has_project_access(proj_id uuid, min_role dto_role)
returns boolean language sql stable as $$
  select exists (
    select 1 from project_members pm
    join users u on u.id = pm.user_id
    where pm.project_id = proj_id
      and pm.user_id = auth.uid()
      and pm.dto_role::text >= min_role::text
  ) or (
    -- OWNER和REGULATOR可以访问所有项目
    select dto_role in ('OWNER','REGULATOR') from users where id = auth.uid()
  );
$$;

-- ── enterprises：只能看自己企业 ──
create policy "企业：本企业可见"
  on enterprises for select
  using (id = current_enterprise_id());

create policy "企业：OWNER可更新"
  on enterprises for update
  using (id = current_enterprise_id() and current_user_role() = 'OWNER');

-- ── users：同企业可见，OWNER可管理 ──
create policy "用户：同企业可见"
  on users for select
  using (enterprise_id = current_enterprise_id());

create policy "用户：本人可更新"
  on users for update
  using (id = auth.uid());

create policy "用户：OWNER可管理"
  on users for all
  using (enterprise_id = current_enterprise_id()
    and current_user_role() in ('OWNER', 'SUPERVISOR'));

-- ── projects：按企业隔离 ──
create policy "项目：本企业可见"
  on projects for select
  using (enterprise_id = current_enterprise_id());

create policy "项目：SUPERVISOR+可创建"
  on projects for insert
  with check (enterprise_id = current_enterprise_id()
    and current_user_role() in ('OWNER','SUPERVISOR'));

create policy "项目：SUPERVISOR+可更新"
  on projects for update
  using (enterprise_id = current_enterprise_id()
    and current_user_role() in ('OWNER','SUPERVISOR'));

-- ── inspections：按企业隔离，AI角色可写入 ──
create policy "质检：本企业可见"
  on inspections for select
  using (enterprise_id = current_enterprise_id());

create policy "质检：AI+可录入"
  on inspections for insert
  with check (enterprise_id = current_enterprise_id()
    and current_user_role() in ('AI','SUPERVISOR','OWNER'));

create policy "质检：SUPERVISOR+可更新"
  on inspections for update
  using (enterprise_id = current_enterprise_id()
    and current_user_role() in ('SUPERVISOR','OWNER'));

-- ── photos：按企业隔离 ──
create policy "照片：本企业可见"
  on photos for select
  using (enterprise_id = current_enterprise_id());

create policy "照片：AI+可上传"
  on photos for insert
  with check (enterprise_id = current_enterprise_id()
    and current_user_role() in ('AI','SUPERVISOR','OWNER'));

-- ── reports：按企业隔离 ──
create policy "报告：本企业可见"
  on reports for select
  using (enterprise_id = current_enterprise_id());

create policy "报告：SUPERVISOR+可生成"
  on reports for insert
  with check (enterprise_id = current_enterprise_id()
    and current_user_role() in ('SUPERVISOR','OWNER'));

-- ── proof_chain：只读（不允许用户直接修改）──
create policy "Proof：本企业可查"
  on proof_chain for select
  using (enterprise_id = current_enterprise_id());

-- REGULATOR 可跨企业查询 Proof
create policy "Proof：监管机构全局查"
  on proof_chain for select
  using (current_user_role() = 'REGULATOR');

-- ── v_nodes：按企业隔离 ──
create policy "节点：本企业可见"
  on v_nodes for select
  using (enterprise_id = current_enterprise_id());

-- PUBLIC 节点全局可见
create policy "节点：PUBLIC节点公开"
  on v_nodes for select
  using (metadata->>'visibility' = 'PUBLIC');

-- ────────────────────────────────────────
-- 6. 触发器（自动维护）
-- ────────────────────────────────────────

-- ── 自动更新 updated_at ──
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger trg_enterprises_updated
  before update on enterprises
  for each row execute function update_updated_at();

create trigger trg_projects_updated
  before update on projects
  for each row execute function update_updated_at();

create trigger trg_v_nodes_updated
  before update on v_nodes
  for each row execute function update_updated_at();

-- ── 质检记录写入时自动生成 v:// URI ──
create or replace function set_inspection_v_uri()
returns trigger language plpgsql as $$
declare
  proj_uri text;
begin
  select v_uri into proj_uri from projects where id = new.project_id;
  new.v_uri := proj_uri || 'inspection/' || new.id::text || '/';
  return new;
end;
$$;

create trigger trg_inspection_v_uri
  before insert on inspections
  for each row execute function set_inspection_v_uri();

-- ── 质检记录写入时更新项目统计 ──
create or replace function update_project_stats()
returns trigger language plpgsql as $$
begin
  update projects set
    record_count = (select count(*) from inspections where project_id = new.project_id),
    updated_at = now()
  where id = new.project_id;
  return new;
end;
$$;

create trigger trg_update_project_stats
  after insert or delete on inspections
  for each row execute function update_project_stats();

-- ── 照片写入时更新项目照片数 ──
create or replace function update_project_photo_count()
returns trigger language plpgsql as $$
begin
  update projects set
    photo_count = (select count(*) from photos where project_id = new.project_id),
    updated_at = now()
  where id = new.project_id;
  return new;
end;
$$;

create trigger trg_update_photo_count
  after insert or delete on photos
  for each row execute function update_project_photo_count();

-- ── 自动注册 v:// 节点 ──
create or replace function auto_register_v_node()
returns trigger language plpgsql as $$
begin
  -- 项目注册时自动创建节点
  if TG_TABLE_NAME = 'projects' then
    insert into v_nodes (uri, parent_uri, node_type, enterprise_id, object_id, object_table)
    values (
      new.v_uri,
      (select v_uri from enterprises where id = new.enterprise_id),
      'Project',
      new.enterprise_id,
      new.id,
      'projects'
    ) on conflict (uri) do nothing;
  end if;

  -- 报告生成时自动创建节点
  if TG_TABLE_NAME = 'reports' then
    insert into v_nodes (uri, parent_uri, node_type, enterprise_id, object_id, object_table)
    values (
      new.v_uri,
      (select v_uri from projects where id = new.project_id),
      'Report',
      new.enterprise_id,
      new.id,
      'reports'
    ) on conflict (uri) do nothing;
  end if;

  return new;
end;
$$;

create trigger trg_register_project_node
  after insert on projects
  for each row execute function auto_register_v_node();

create trigger trg_register_report_node
  after insert on reports
  for each row execute function auto_register_v_node();

-- ────────────────────────────────────────
-- 7. 核心函数（API层调用）
-- ────────────────────────────────────────

-- ── 生成 Proof Hash ──
create or replace function generate_proof(
  p_v_uri      text,
  p_object_type text,
  p_object_id  uuid,
  p_actor_id   uuid,
  p_summary    text,
  p_payload    jsonb default '{}'
) returns text language plpgsql security definer as $$
declare
  v_proof_id    text;
  v_proof_hash  text;
  v_parent_hash text;
  v_payload_str text;
  v_enterprise_id uuid;
  v_project_id  uuid;
begin
  -- 拉取企业和项目ID
  select enterprise_id into v_enterprise_id
  from users where id = p_actor_id;

  select id into v_project_id
  from projects where enterprise_id = v_enterprise_id
    and v_uri = split_part(p_v_uri, '/inspection/', 1) || '/'
  limit 1;

  -- 获取最新Proof的哈希（链式引用）
  select proof_hash into v_parent_hash
  from proof_chain
  where v_uri = p_v_uri
  order by created_at desc
  limit 1;

  -- 生成Proof内容
  v_payload_str := jsonb_build_object(
    'uri',        p_v_uri,
    'type',       p_object_type,
    'object_id',  p_object_id,
    'actor',      p_actor_id,
    'parent',     coalesce(v_parent_hash, 'GENESIS'),
    'timestamp',  extract(epoch from now())::bigint,
    'payload',    p_payload
  )::text;

  -- SHA256哈希
  v_proof_hash := encode(digest(v_payload_str, 'sha256'), 'hex');

  -- 生成Proof ID
  v_proof_id := 'GP-PROOF-' || upper(substring(v_proof_hash, 1, 16));

  -- 写入Proof链
  insert into proof_chain (
    proof_id, proof_hash, parent_hash,
    enterprise_id, project_id,
    v_uri, object_type, object_id,
    action, actor_id, summary,
    payload_hash, status
  ) values (
    v_proof_id, v_proof_hash, v_parent_hash,
    v_enterprise_id, v_project_id,
    p_v_uri, p_object_type, p_object_id,
    'create', p_actor_id, p_summary,
    encode(digest(p_payload::text, 'sha256'), 'hex'),
    'confirmed'
  );

  -- 更新对象的Proof字段
  if p_object_type = 'inspection' then
    update inspections set
      proof_id = v_proof_id,
      proof_hash = v_proof_hash,
      proof_status = 'confirmed'
    where id = p_object_id;
  elsif p_object_type = 'report' then
    update reports set
      proof_id = v_proof_id,
      proof_hash = v_proof_hash,
      proof_status = 'confirmed'
    where id = p_object_id;
  end if;

  -- 更新节点Peg计数
  update v_nodes set
    peg_count = peg_count + 1,
    last_peg_at = now()
  where uri = p_v_uri;

  return v_proof_id;
end;
$$;

-- ── 质检记录提交（含自动Proof）──
create or replace function submit_inspection(
  p_project_id   uuid,
  p_location     text,
  p_type         text,
  p_type_name    text,
  p_value        numeric,
  p_standard     numeric,
  p_unit         text,
  p_result       inspect_result,
  p_person       text,
  p_remark       text default null,
  p_inspected_at timestamptz default now()
) returns jsonb language plpgsql security definer as $$
declare
  v_insp_id   uuid;
  v_proof_id  text;
  v_ent_id    uuid;
  v_v_uri     text;
begin
  -- 获取企业ID
  select enterprise_id into v_ent_id
  from users where id = auth.uid();

  -- 插入质检记录
  insert into inspections (
    project_id, enterprise_id,
    location, type, type_name,
    value, standard, unit,
    result, person, person_id, remark,
    inspected_at
  ) values (
    p_project_id, v_ent_id,
    p_location, p_type, p_type_name,
    p_value, p_standard, p_unit,
    p_result, p_person, auth.uid(), p_remark,
    p_inspected_at
  ) returning id, v_uri into v_insp_id, v_v_uri;

  -- 自动生成Proof
  v_proof_id := generate_proof(
    v_v_uri,
    'inspection',
    v_insp_id,
    auth.uid(),
    format('质检录入·%s·%s·%s', p_type_name, p_location, p_result::text),
    jsonb_build_object(
      'value', p_value,
      'standard', p_standard,
      'result', p_result
    )
  );

  return jsonb_build_object(
    'inspection_id', v_insp_id,
    'v_uri', v_v_uri,
    'proof_id', v_proof_id
  );
end;
$$;

-- ── 查询项目合格率统计 ──
create or replace function get_project_stats(p_project_id uuid)
returns jsonb language sql stable as $$
  select jsonb_build_object(
    'total',     count(*),
    'pass',      count(*) filter (where result = 'pass'),
    'warn',      count(*) filter (where result = 'warn'),
    'fail',      count(*) filter (where result = 'fail'),
    'pass_rate', round(
      count(*) filter (where result = 'pass')::numeric / nullif(count(*),0) * 100, 1
    ),
    'latest_at', max(inspected_at)
  )
  from inspections
  where project_id = p_project_id;
$$;

-- ── 查询 v:// 节点树 ──
create or replace function get_v_node_tree(p_root_uri text)
returns table(
  uri        text,
  parent_uri text,
  node_type  node_type,
  depth      int,
  peg_count  int,
  status     text
) language sql stable as $$
  with recursive tree as (
    select uri, parent_uri, node_type, 0 as depth, peg_count, status
    from v_nodes where uri = p_root_uri

    union all

    select n.uri, n.parent_uri, n.node_type, t.depth + 1, n.peg_count, n.status
    from v_nodes n
    join tree t on n.parent_uri = t.uri
    where t.depth < 10
  )
  select * from tree order by depth, uri;
$$;

-- ── 生成质检报告（汇总数据）──
create or replace function generate_report_data(
  p_project_id  uuid,
  p_location    text default null,
  p_date_from   date default current_date - 7,
  p_date_to     date default current_date
) returns jsonb language sql stable as $$
  select jsonb_build_object(
    'records', jsonb_agg(
      jsonb_build_object(
        'id',        id,
        'location',  location,
        'type',      type,
        'type_name', type_name,
        'value',     value,
        'standard',  standard,
        'unit',      unit,
        'result',    result,
        'person',    person,
        'remark',    remark,
        'proof_id',  proof_id,
        'at',        inspected_at
      ) order by inspected_at
    ),
    'stats', jsonb_build_object(
      'total',     count(*),
      'pass',      count(*) filter (where result='pass'),
      'warn',      count(*) filter (where result='warn'),
      'fail',      count(*) filter (where result='fail'),
      'pass_rate', round(count(*) filter(where result='pass')::numeric / nullif(count(*),0)*100,1)
    )
  )
  from inspections
  where project_id = p_project_id
    and (p_location is null or location = p_location)
    and inspected_at::date between p_date_from and p_date_to;
$$;

-- ────────────────────────────────────────
-- 8. Storage Buckets（照片存储）
-- ────────────────────────────────────────

-- 在 Supabase Dashboard 执行以下操作：
-- Storage → New Bucket → "qcspec-photos"（private）
-- Storage → New Bucket → "qcspec-reports"（private）
-- Storage → New Bucket → "qcspec-templates"（private）

-- 照片访问策略（企业隔离）
-- insert into storage.policies (bucket_id, name, definition)
-- values (
--   'qcspec-photos',
--   '企业照片隔离',
--   'bucket_id = ''qcspec-photos'' and auth.uid() in (
--     select id from users where enterprise_id = current_enterprise_id()
--   )'
-- );

-- ────────────────────────────────────────
-- 9. 初始数据（种子数据）
-- ────────────────────────────────────────

-- 插入中北工程作为首个企业节点
insert into enterprises (
  v_uri, name, short_name, domain,
  industry, plan, proof_quota
) values (
  'v://cn.中北/',
  '中北工程设计咨询有限公司',
  '中北工程',
  'zhongbei.com',
  '工程建设 / 设计院',
  'enterprise',
  99999
) on conflict (v_uri) do nothing;

-- 注释：以下用户在应用层通过 Supabase Auth 创建
-- 此处仅作结构说明
/*
insert into users (enterprise_id, v_uri, name, email, dto_role, title)
values (
  (select id from enterprises where v_uri = 'v://cn.中北/'),
  'v://cn.中北/executor/李总工/',
  '李总工', 'admin@zhongbei.com', 'OWNER', '总工程师'
);
*/

-- 企业默认配置
insert into enterprise_configs (enterprise_id)
select id from enterprises where v_uri = 'v://cn.中北/'
on conflict (enterprise_id) do nothing;

-- ────────────────────────────────────────
-- 10. Realtime（实时订阅）
-- ────────────────────────────────────────

-- 在 Supabase Dashboard → Database → Replication 启用以下表：
-- inspections（质检员实时看到新记录）
-- proof_chain（Proof实时上链通知）
-- reports（报告生成完成通知）

-- 或通过 SQL：
alter publication supabase_realtime
  add table inspections, proof_chain, reports, photos;

-- ════════════════════════════════════════════════════════
-- 使用说明
-- ════════════════════════════════════════════════════════
--
-- 前端调用示例（JavaScript）：
--
-- // 1. 提交质检记录（自动生成Proof）
-- const { data } = await supabase.rpc('submit_inspection', {
--   p_project_id: 'uuid...',
--   p_location: 'K50+200',
--   p_type: 'flatness',
--   p_type_name: '路面平整度',
--   p_value: 1.8,
--   p_standard: 2.0,
--   p_unit: 'm/km',
--   p_result: 'pass',
--   p_person: '张工',
-- });
-- // 返回：{ inspection_id, v_uri, proof_id }
--
-- // 2. 查询项目统计
-- const { data } = await supabase.rpc('get_project_stats', {
--   p_project_id: 'uuid...'
-- });
-- // 返回：{ total, pass, warn, fail, pass_rate, latest_at }
--
-- // 3. 实时订阅质检记录
-- supabase.channel('inspections')
--   .on('postgres_changes',
--     { event: 'INSERT', schema: 'public', table: 'inspections' },
--     payload => console.log('新质检记录:', payload.new)
--   ).subscribe();
--
-- // 4. 查询 v:// 节点树
-- const { data } = await supabase.rpc('get_v_node_tree', {
--   p_root_uri: 'v://cn.中北/'
-- });
--
-- ════════════════════════════════════════════════════════
-- 后续接入 GitPeg 生产环境 API
-- ════════════════════════════════════════════════════════
--
-- 替换 generate_proof() 函数中的本地哈希逻辑：
-- → POST https://api.gitpeg.dev/v1/proof/commit
--
-- 替换 auto_register_v_node() 触发器：
-- → POST https://api.gitpeg.dev/v1/nodes/register
--
-- ════════════════════════════════════════════════════════
