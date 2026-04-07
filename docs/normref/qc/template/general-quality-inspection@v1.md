# v://normref.com/qc/template/general-quality-inspection@v1

**Layer 1: Header����ݲ㣩**
- normref_uri: v://normref.com/qc/[��������]@v1
- doc_type: quality-inspection
- jurisdiction: [GB50204 / JTG F80 / SL223 ��]
- industry: highway / bridge / water
- version: v1

**Layer 2: Gate���ż��㣩**
- required_trip_roles: ["inspector.quality.check", "supervisor.approve"]
- pre_conditions: ["ԭ���Ϻϸ�", "�豸У׼��Ч"]
- entry_rules: []

**Layer 3: Body�����ݲ㣩**
- basic: { location, component_type, quantity }
- test_data: [{ item, standard, measured, unit, result }]
- relations: [v://...]

**Layer 4: Proof��֤���㣩**
- signatures: []
- data_hash: sha256
- witness_logs: []
- proof_hash: string

**Layer 5: State��״̬�㣩**
- lifecycle_stage: draft/pending_review/approved/archived
- state_matrix: { total_tables, generated, signed, pending }
- next_action: string
