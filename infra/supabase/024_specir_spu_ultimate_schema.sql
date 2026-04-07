-- Upgrade baseline SPU objects to the Ultimate SPU schema.
-- Mandatory module blocks:
--   identity / measure_rule / consumption / qc_gate
-- Keep compatibility aliases for existing runtime readers.

create extension if not exists pgcrypto;

with seed(uri, title, content, metadata, status) as (
  values
  (
    'v://norm/spu/rebar-processing@v1',
    'Rebar processing and installation',
    '{
      "schema":"qcspec.specir.spu.ultimate",
      "schema_version":"1.0.0",
      "identity":{
        "spu_uri":"v://norm/spu/rebar-processing@v1",
        "sovereignty_uri":"v://norm",
        "industry":"Highway",
        "standard_codes":["GB50204-2015"],
        "category_path":["rebar-processing"],
        "aliases":[],
        "authority_refs":[]
      },
      "measure_rule":{
        "unit":"t",
        "payable_unit":"t",
        "meter_rule_ref":"v://norm/meter-rule/by-weight@v1",
        "statement":"Meter by net rebar weight.",
        "algorithm":{
          "key":"weight-net",
          "expression":"quantity_ton",
          "description":"",
          "parameters":{},
          "exclusion_rules":[]
        },
        "settlement_clauses":[],
        "examples":[]
      },
      "consumption":{
        "unit_basis":"t",
        "quota_ref":"v://norm/quota/rebar-processing@v1",
        "materials":[{"code":"","name":"Rebar","unit":"t","quantity_per_unit":1.0,"remark":"","source_ref":""}],
        "machinery":[],
        "labor":[],
        "notes":[]
      },
      "qc_gate":{
        "strategy":"all_pass",
        "fail_action":"trigger_review_trip",
        "gate_refs":[
          "v://norm/gate/rebar-diameter-check@v1",
          "v://norm/gate/rebar-spacing-check@v1"
        ],
        "rules":[],
        "checklist":[]
      },
      "extensions":{},
      "schema_modules":["Identity","MeasureRule","Consumption","QCGate"],
      "label":"Rebar processing and installation",
      "unit":"t",
      "norm_refs":["GB50204-2015"],
      "gate_refs":[
        "v://norm/gate/rebar-diameter-check@v1",
        "v://norm/gate/rebar-spacing-check@v1"
      ],
      "quota_ref":"v://norm/quota/rebar-processing@v1",
      "meter_rule_ref":"v://norm/meter-rule/by-weight@v1",
      "quota_refs":["v://norm/quota/rebar-processing@v1"],
      "meter_rule_refs":["v://norm/meter-rule/by-weight@v1"]
    }'::jsonb,
    '{"domain":"qcspec","seed":"024","upgrade":"spu_ultimate"}'::jsonb,
    'active'
  ),
  (
    'v://norm/spu/pier-concrete-casting@v1',
    'Bridge pier concrete casting',
    '{
      "schema":"qcspec.specir.spu.ultimate",
      "schema_version":"1.0.0",
      "identity":{
        "spu_uri":"v://norm/spu/pier-concrete-casting@v1",
        "sovereignty_uri":"v://norm",
        "industry":"Highway",
        "standard_codes":["GB50204-2015"],
        "category_path":["pier-concrete-casting"],
        "aliases":[],
        "authority_refs":[]
      },
      "measure_rule":{
        "unit":"m3",
        "payable_unit":"m3",
        "meter_rule_ref":"v://norm/meter-rule/by-volume@v1",
        "statement":"Volume by design section and pile length; over-pour not payable.",
        "algorithm":{
          "key":"design-section-volume",
          "expression":"design_area * design_length",
          "description":"",
          "parameters":{},
          "exclusion_rules":["over-pour-not-payable"]
        },
        "settlement_clauses":[],
        "examples":[]
      },
      "consumption":{
        "unit_basis":"m3",
        "quota_ref":"v://norm/quota/concrete-casting@v1",
        "materials":[
          {"code":"","name":"Cement","unit":"kg","quantity_per_unit":350.0,"remark":"","source_ref":""},
          {"code":"","name":"Water","unit":"kg","quantity_per_unit":180.0,"remark":"","source_ref":""}
        ],
        "machinery":[
          {"code":"","name":"Concrete pump shift","unit":"shift","quantity_per_unit":0.05,"remark":"","source_ref":""}
        ],
        "labor":[],
        "notes":[]
      },
      "qc_gate":{
        "strategy":"all_pass",
        "fail_action":"trigger_review_trip",
        "gate_refs":["v://norm/gate/concrete-strength-check@v1"],
        "rules":[
          {"metric":"slump","operator":"range","threshold":[180,220],"unit":"mm","spec_ref":"","gate_ref":"","sample_frequency":"","required":true},
          {"metric":"pile-position-offset","operator":"<=","threshold":50,"unit":"mm","spec_ref":"","gate_ref":"","sample_frequency":"","required":true}
        ],
        "checklist":[]
      },
      "extensions":{},
      "schema_modules":["Identity","MeasureRule","Consumption","QCGate"],
      "label":"Bridge pier concrete casting",
      "unit":"m3",
      "norm_refs":["GB50204-2015"],
      "gate_refs":["v://norm/gate/concrete-strength-check@v1"],
      "quota_ref":"v://norm/quota/concrete-casting@v1",
      "meter_rule_ref":"v://norm/meter-rule/by-volume@v1",
      "quota_refs":["v://norm/quota/concrete-casting@v1"],
      "meter_rule_refs":["v://norm/meter-rule/by-volume@v1"]
    }'::jsonb,
    '{"domain":"qcspec","seed":"024","upgrade":"spu_ultimate"}'::jsonb,
    'active'
  ),
  (
    'v://norm/spu/pavement-laying@v1',
    'Pavement laying',
    '{
      "schema":"qcspec.specir.spu.ultimate",
      "schema_version":"1.0.0",
      "identity":{
        "spu_uri":"v://norm/spu/pavement-laying@v1",
        "sovereignty_uri":"v://norm",
        "industry":"Highway",
        "standard_codes":["JTG F80/1-2017"],
        "category_path":["pavement-laying"],
        "aliases":[],
        "authority_refs":[]
      },
      "measure_rule":{
        "unit":"m2",
        "payable_unit":"m2",
        "meter_rule_ref":"v://norm/meter-rule/by-area@v1",
        "statement":"Meter by designed paving area.",
        "algorithm":{
          "key":"area-design",
          "expression":"length * width",
          "description":"",
          "parameters":{},
          "exclusion_rules":[]
        },
        "settlement_clauses":[],
        "examples":[]
      },
      "consumption":{
        "unit_basis":"m2",
        "quota_ref":"v://norm/quota/pavement-laying@v1",
        "materials":[],
        "machinery":[],
        "labor":[],
        "notes":[]
      },
      "qc_gate":{
        "strategy":"all_pass",
        "fail_action":"trigger_review_trip",
        "gate_refs":["v://norm/gate/pavement-flatness-check@v1"],
        "rules":[],
        "checklist":[]
      },
      "extensions":{},
      "schema_modules":["Identity","MeasureRule","Consumption","QCGate"],
      "label":"Pavement laying",
      "unit":"m2",
      "norm_refs":["JTG F80/1-2017"],
      "gate_refs":["v://norm/gate/pavement-flatness-check@v1"],
      "quota_ref":"v://norm/quota/pavement-laying@v1",
      "meter_rule_ref":"v://norm/meter-rule/by-area@v1",
      "quota_refs":["v://norm/quota/pavement-laying@v1"],
      "meter_rule_refs":["v://norm/meter-rule/by-area@v1"]
    }'::jsonb,
    '{"domain":"qcspec","seed":"024","upgrade":"spu_ultimate"}'::jsonb,
    'active'
  ),
  (
    'v://norm/spu/contract-payment@v1',
    'Contract payment item',
    '{
      "schema":"qcspec.specir.spu.ultimate",
      "schema_version":"1.0.0",
      "identity":{
        "spu_uri":"v://norm/spu/contract-payment@v1",
        "sovereignty_uri":"v://norm",
        "industry":"Highway",
        "standard_codes":["Contract-Clauses"],
        "category_path":["contract-payment"],
        "aliases":[],
        "authority_refs":[]
      },
      "measure_rule":{
        "unit":"CNY",
        "payable_unit":"CNY",
        "meter_rule_ref":"v://norm/meter-rule/contract-payment@v1",
        "statement":"Meter by approved claimed amount.",
        "algorithm":{
          "key":"contract-claim",
          "expression":"claimed_amount",
          "description":"",
          "parameters":{},
          "exclusion_rules":[]
        },
        "settlement_clauses":[],
        "examples":[]
      },
      "consumption":{
        "unit_basis":"CNY",
        "quota_ref":"v://norm/quota/contract-payment@v1",
        "materials":[],
        "machinery":[],
        "labor":[],
        "notes":[]
      },
      "qc_gate":{
        "strategy":"all_pass",
        "fail_action":"trigger_review_trip",
        "gate_refs":[],
        "rules":[],
        "checklist":[]
      },
      "extensions":{},
      "schema_modules":["Identity","MeasureRule","Consumption","QCGate"],
      "label":"Contract payment item",
      "unit":"CNY",
      "norm_refs":["Contract-Clauses"],
      "gate_refs":[],
      "quota_ref":"v://norm/quota/contract-payment@v1",
      "meter_rule_ref":"v://norm/meter-rule/contract-payment@v1",
      "quota_refs":["v://norm/quota/contract-payment@v1"],
      "meter_rule_refs":["v://norm/meter-rule/contract-payment@v1"]
    }'::jsonb,
    '{"domain":"qcspec","seed":"024","upgrade":"spu_ultimate"}'::jsonb,
    'active'
  ),
  (
    'v://norm/spu/landscape-work@v1',
    'Landscape work',
    '{
      "schema":"qcspec.specir.spu.ultimate",
      "schema_version":"1.0.0",
      "identity":{
        "spu_uri":"v://norm/spu/landscape-work@v1",
        "sovereignty_uri":"v://norm",
        "industry":"Municipal",
        "standard_codes":["Landscape-Acceptance"],
        "category_path":["landscape-work"],
        "aliases":[],
        "authority_refs":[]
      },
      "measure_rule":{
        "unit":"m2",
        "payable_unit":"m2",
        "meter_rule_ref":"v://norm/meter-rule/landscape-work@v1",
        "statement":"Meter by planted/covered area.",
        "algorithm":{
          "key":"landscape-area",
          "expression":"length * width",
          "description":"",
          "parameters":{},
          "exclusion_rules":[]
        },
        "settlement_clauses":[],
        "examples":[]
      },
      "consumption":{
        "unit_basis":"m2",
        "quota_ref":"v://norm/quota/landscape-work@v1",
        "materials":[],
        "machinery":[],
        "labor":[],
        "notes":[]
      },
      "qc_gate":{
        "strategy":"all_pass",
        "fail_action":"trigger_review_trip",
        "gate_refs":[],
        "rules":[],
        "checklist":[]
      },
      "extensions":{},
      "schema_modules":["Identity","MeasureRule","Consumption","QCGate"],
      "label":"Landscape work",
      "unit":"m2",
      "norm_refs":["Landscape-Acceptance"],
      "gate_refs":[],
      "quota_ref":"v://norm/quota/landscape-work@v1",
      "meter_rule_ref":"v://norm/meter-rule/landscape-work@v1",
      "quota_refs":["v://norm/quota/landscape-work@v1"],
      "meter_rule_refs":["v://norm/meter-rule/landscape-work@v1"]
    }'::jsonb,
    '{"domain":"qcspec","seed":"024","upgrade":"spu_ultimate"}'::jsonb,
    'active'
  )
)
insert into public.specir_objects (
  uri,
  kind,
  version,
  title,
  content,
  content_hash,
  status,
  metadata
)
select
  s.uri,
  'spu' as kind,
  coalesce(nullif(split_part(s.uri, '@', 2), ''), 'v1') as version,
  s.title,
  s.content,
  encode(digest(convert_to(coalesce(s.content::text, ''), 'utf8'), 'sha256'), 'hex') as content_hash,
  s.status,
  s.metadata
from seed s
on conflict (uri) do update
set
  kind = excluded.kind,
  version = excluded.version,
  title = excluded.title,
  content = excluded.content,
  content_hash = excluded.content_hash,
  status = excluded.status,
  metadata = excluded.metadata,
  updated_at = now();
