import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import PublicVerifyPage from './pages/PublicVerifyPage'

// 注入全局样式
const style = document.createElement('style')
style.textContent = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@900&family=Noto+Sans+SC:wght@400;500;700&family=JetBrains+Mono:wght@400;700&display=swap');
  :root {
    --bg:#F0F4F8;
    --white:#FFFFFF;
    --blue:#1A56DB;
    --blue2:#2563EB;
    --blue-l:#EFF6FF;
    --cyan:#0891B2;
    --cyan-l:#ECFEFF;
    --green:#059669;
    --green-l:#ECFDF5;
    --red:#DC2626;
    --red-l:#FEF2F2;
    --gold:#D97706;
    --gold-l:#FFFBEB;
    --purple:#7C3AED;
    --purple-l:#F5F3FF;
    --gray:#6B7280;
    --gray2:#9CA3AF;
    --border:#E2E8F0;
    --dark:#0F172A;
    --text:#334155;
    --mono:'JetBrains Mono',monospace;
    --sans:'Noto Sans SC',sans-serif;
  }
  *{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
  html,body,#root{height:100%}
  html{scroll-behavior:smooth}
  body{font-family:var(--sans);background:var(--bg);color:var(--text)}

  .login-screen{
    min-height:100vh;display:flex;align-items:center;justify-content:center;
    background:linear-gradient(135deg,#0F172A 0%,#1E3A5F 50%,#0F172A 100%);
    padding:24px;position:relative;overflow:hidden;
  }
  .login-screen::before{
    content:'';position:absolute;inset:0;
    background:radial-gradient(ellipse 60% 60% at 50% 30%,rgba(26,86,219,0.15),transparent);
  }
  .login-card{
    background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);backdrop-filter:blur(20px);
    border-radius:20px;padding:40px;width:100%;max-width:420px;position:relative;
  }
  .login-logo{text-align:center;margin-bottom:28px}
  .login-brand{font-family:var(--mono);font-size:32px;font-weight:900;letter-spacing:-1px}
  .login-brand .qc{color:#60A5FA}
  .login-brand .spec{color:#34D399}
  .login-tagline{font-size:13px;color:#64748B;margin-top:6px}
  .login-tab{display:flex;background:rgba(255,255,255,0.05);border-radius:10px;margin-bottom:24px;padding:4px;gap:4px}
  .ltab{
    flex:1;padding:10px;text-align:center;font-size:13px;font-weight:700;color:#64748B;border-radius:7px;
    cursor:pointer;transition:all .2s;border:none;background:transparent;font-family:var(--sans);
  }
  .ltab.active{background:var(--blue);color:#fff}
  .login-form{display:flex;flex-direction:column;gap:12px}
  .l-input{
    width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);
    border-radius:8px;padding:12px 14px;font-size:14px;font-family:var(--sans);color:#fff;outline:none;transition:all .2s;
  }
  .l-input:focus{border-color:#60A5FA;background:rgba(255,255,255,0.1)}
  .l-input::placeholder{color:#475569}
  .l-btn{
    padding:14px;background:var(--blue);color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;
    font-family:var(--sans);box-shadow:0 4px 16px rgba(26,86,219,0.4);transition:all .2s;margin-top:4px;
  }
  .l-btn:active{transform:scale(0.98)}
  .l-hint{font-size:12px;color:#64748B;text-align:center}
  .demo-accounts{
    margin-top:4px;padding:12px;background:rgba(255,255,255,0.04);
    border-radius:8px;border:1px solid rgba(255,255,255,0.06);
  }
  .demo-title{font-size:12px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px}
  .demo-item{
    padding:8px 10px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);
    border-radius:6px;margin-bottom:8px;
  }
  .demo-item:last-child{margin-bottom:0}
  .demo-line{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:12px;color:#CBD5E1}
  .demo-line strong{color:#60A5FA}
  .demo-subline{margin-top:4px;font-size:12px;color:#94A3B8}
  .demo-actions{display:flex;gap:8px;margin-top:8px}
  .demo-btn{
    flex:1;text-align:center;padding:6px 10px;border:1px solid rgba(255,255,255,0.14);
    border-radius:6px;cursor:pointer;font-size:12px;font-family:var(--sans);transition:all .2s;
  }
  .demo-btn-ghost{background:rgba(255,255,255,0.03);color:#CBD5E1}
  .demo-btn-ghost:hover{background:rgba(255,255,255,0.09);color:#fff}
  .demo-btn-primary{background:rgba(37,99,235,0.92);border-color:rgba(59,130,246,1);color:#fff}
  .demo-btn-primary:hover{background:#2563EB}

  .app-shell{display:flex;min-height:100vh}
  .sidebar{
    position:fixed;top:0;left:0;bottom:0;width:220px;
    background:var(--dark);z-index:200;display:flex;flex-direction:column;
    border-right:1px solid rgba(255,255,255,0.05);transition:transform .25s;
  }
  .sidebar-brand{padding:20px 18px;border-bottom:1px solid rgba(255,255,255,.06)}
  .sb-logo{font-family:var(--mono);font-size:20px;font-weight:900;letter-spacing:-.5px}
  .sb-logo .qc{color:#60A5FA}
  .sb-logo .spec{color:#34D399}
  .sb-version{font-size:12px;color:#374151;font-family:var(--mono);margin-top:2px}
  .sidebar-nav{flex:1;padding:12px 0;overflow-y:auto}
  .nav-section{padding:0 14px;margin-bottom:4px}
  .nav-section-label{
    font-size:12px;color:#374151;letter-spacing:2px;text-transform:uppercase;
    padding:8px 4px 4px;font-weight:700;
  }
  .nav-item{
    display:flex;align-items:center;gap:10px;padding:10px 10px;border-radius:8px;margin-bottom:2px;
    cursor:pointer;transition:all .2s;color:#6B7280;font-size:13px;font-weight:500;
  }
  .nav-item:hover{background:rgba(255,255,255,.05);color:#E5E7EB}
  .nav-item.active{background:rgba(26,86,219,.15);color:#60A5FA;font-weight:700}
  .nav-icon{font-size:16px;width:20px;text-align:center;flex-shrink:0}
  .nav-badge{
    margin-left:auto;background:var(--blue);color:#fff;font-size:12px;font-weight:700;
    padding:1px 6px;border-radius:8px;
  }
  .sidebar-footer{padding:14px;border-top:1px solid rgba(255,255,255,.06)}
  .user-card{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;cursor:pointer;transition:background .2s}
  .user-card:hover{background:rgba(255,255,255,.05)}
  .user-avatar{
    width:34px;height:34px;border-radius:50%;
    background:linear-gradient(135deg,var(--blue),#7C3AED);
    display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:700;flex-shrink:0;
  }
  .user-info{flex:1;min-width:0}
  .user-name{font-size:13px;color:#E5E7EB;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .user-role{font-size:12px;color:#475569}
  .logout-btn{font-size:12px;color:#374151;cursor:pointer;padding:4px;border-radius:4px;transition:color .2s}
  .logout-btn:hover{color:#EF4444}

  .main-content{margin-left:220px;min-height:100vh;display:flex;flex-direction:column;flex:1}
  .topbar{
    background:var(--white);border-bottom:1px solid var(--border);
    padding:0 24px;height:56px;display:flex;align-items:center;justify-content:space-between;
    position:sticky;top:0;z-index:100;
  }
  .topbar-title{font-size:16px;font-weight:700;color:var(--dark)}
  .topbar-right{display:flex;gap:10px;align-items:center}
  .topbar-btn{
    padding:8px 16px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;font-family:var(--sans);border:none;transition:all .2s;
  }
  .btn-blue{background:var(--blue);color:#fff;box-shadow:0 2px 8px rgba(26,86,219,.3)}
  .btn-outline{background:#fff;color:var(--gray);border:1px solid var(--border)}
  .btn-logout{background:#FEF2F2;color:#B91C1C;border:1px solid #FECACA}
  .btn-logout:hover{background:#FEE2E2}
  .content-body{padding:24px;flex:1}

  .dash-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}
  .stat-card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:16px;display:flex;align-items:center;gap:14px}
  .stat-icon{
    width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;
    font-size:20px;flex-shrink:0;
  }
  .si-blue{background:var(--blue-l)}
  .si-green{background:var(--green-l)}
  .si-gold{background:var(--gold-l)}
  .si-purple{background:var(--purple-l)}
  .stat-val{font-size:26px;font-weight:900;color:var(--dark);line-height:1}
  .stat-label{font-size:12px;color:var(--gray);margin-top:3px}
  .stat-trend{font-size:12px;margin-top:4px}
  .trend-up{color:var(--green)}
  .trend-down{color:var(--red)}
  .dash-grid{display:grid;grid-template-columns:2fr 1fr;gap:16px}

  .activity-item{display:flex;align-items:flex-start;gap:12px;padding:12px 0;border-bottom:1px solid var(--border)}
  .activity-item:last-child{border-bottom:none}
  .activity-dot{width:8px;height:8px;border-radius:50%;margin-top:5px;flex-shrink:0}
  .activity-text{font-size:13px;color:var(--text);line-height:1.5}
  .activity-time{font-size:12px;color:var(--gray2);margin-top:2px}
  .quick-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .quick-btn{
    padding:14px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;
    cursor:pointer;transition:all .2s;text-align:center;font-size:12px;font-weight:700;color:var(--dark);font-family:var(--sans);
  }
  .quick-btn:hover{border-color:var(--blue);background:var(--blue-l);color:var(--blue)}
  .quick-btn-icon{font-size:22px;margin-bottom:6px}

  .toolbar{display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap}
  .search-input{
    flex:1;min-width:200px;background:var(--white);border:1px solid var(--border);border-radius:8px;
    padding:9px 14px 9px 36px;font-size:13px;font-family:var(--sans);color:var(--dark);outline:none;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239CA3AF' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'/%3E%3C/svg%3E");
    background-repeat:no-repeat;background-size:16px;background-position:12px center;transition:border-color .2s;
  }
  .search-input:focus{border-color:var(--blue)}
  .filter-select{
    background:var(--white);border:1px solid var(--border);border-radius:8px;padding:9px 14px;
    font-size:13px;font-family:var(--sans);color:var(--dark);outline:none;
  }
  .proj-table{width:100%;border-collapse:collapse}
  .proj-table th{
    text-align:left;font-size:12px;font-weight:700;color:var(--gray);text-transform:uppercase;letter-spacing:.5px;
    padding:10px 14px;border-bottom:2px solid var(--border);background:var(--bg);
  }
  .proj-table td{padding:14px;border-bottom:1px solid var(--border);font-size:13px;color:var(--text);vertical-align:middle}
  .proj-table tr:hover td{background:var(--blue-l)}
  .proj-table tr:last-child td{border-bottom:none}
  .type-chip{display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:6px;font-size:12px;font-weight:700}
  .chip-highway{background:#EFF6FF;color:#1D4ED8}
  .chip-road{background:#F0FDF4;color:#166534}
  .chip-urban{background:#EEF2FF;color:#4338CA}
  .chip-bridge{background:#EEF2FF;color:#4338CA}
  .chip-bridge_repair{background:#FEF3C7;color:#92400E}
  .chip-tunnel{background:#F0F9FF;color:#0369A1}
  .chip-municipal{background:#FFFBEB;color:#92400E}
  .chip-water{background:#ECFEFF;color:#0E7490}
  .status-pill{display:inline-block;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:700}
  .pill-active{background:var(--green-l);color:var(--green)}
  .pill-pending{background:var(--gold-l);color:var(--gold)}
  .pill-closed{background:var(--bg);color:var(--gray)}
  .action-btns{display:flex;gap:6px;flex-wrap:wrap}
  .act-btn{
    padding:5px 10px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;border:none;font-family:var(--sans);transition:all .2s;
  }
  .act-enter{background:var(--blue-l);color:var(--blue)}
  .act-edit{background:var(--bg);color:var(--gray);border:1px solid var(--border)}
  .act-detail{background:#fff;color:var(--dark);border:1px solid var(--border)}
  .act-del{background:var(--red-l);color:var(--red);border:1px solid #FECACA}

  .page{display:none}
  .page.active{display:block}

  .reg-steps{
    display:flex;gap:0;margin-bottom:16px;
    background:#fff;border:1px solid var(--border);border-radius:12px;overflow:hidden;
  }
  .reg-step{
    flex:1;padding:12px 10px;text-align:center;border-right:1px solid var(--border);
    background:#fff;transition:all .2s;
  }
  .reg-step:last-child{border-right:none}
  .reg-step.active{background:var(--blue-l)}
  .reg-step.done{background:var(--green-l)}
  .reg-step-num{
    width:26px;height:26px;border-radius:50%;margin:0 auto 6px;
    display:flex;align-items:center;justify-content:center;
    background:#E2E8F0;color:#64748B;font-size:12px;font-weight:700;
  }
  .reg-step.active .reg-step-num{background:var(--blue);color:#fff}
  .reg-step.done .reg-step-num{background:var(--green);color:#fff}
  .reg-step-label{font-size:12px;color:#64748B;font-weight:600}
  .reg-step.active .reg-step-label{color:var(--blue)}
  .reg-step.done .reg-step-label{color:var(--green)}

  .register-hero{
    background:linear-gradient(135deg,#0F172A 0%,#1E3A5F 50%,#0F172A 100%);
    border-radius:14px;padding:28px 22px;margin-bottom:14px;color:#fff;position:relative;overflow:hidden;
  }
  .register-hero::before{
    content:'';position:absolute;inset:0;background:radial-gradient(ellipse 60% 80% at 50% 0%,rgba(26,86,219,.16),transparent);
  }
  .register-eyebrow{
    position:relative;display:inline-block;padding:4px 12px;border-radius:999px;
    background:rgba(52,211,153,.14);border:1px solid rgba(52,211,153,.25);
    color:#34D399;font-family:var(--mono);font-size:12px;letter-spacing:1.4px;text-transform:uppercase;margin-bottom:10px;
  }
  .register-title{position:relative;font-size:26px;line-height:1.2;font-weight:900;margin-bottom:8px}
  .register-title .hl{color:#60A5FA}
  .register-sub{position:relative;font-size:13px;color:#94A3B8;line-height:1.7;max-width:680px}
  .register-hero-stats{position:relative;display:flex;gap:28px;flex-wrap:wrap;margin-top:16px}
  .hero-stat-val{font-family:var(--mono);font-size:24px;font-weight:800;color:#fff;line-height:1}
  .hero-stat-label{font-size:12px;color:#64748B;margin-top:4px}

  .reg-info-box{
    border-radius:8px;padding:11px 12px;display:flex;gap:8px;align-items:flex-start;margin-bottom:10px;
    border:1px solid transparent;
  }
  .reg-info-box.blue{background:#EFF6FF;border-color:#BFDBFE}
  .reg-info-box.green{background:#ECFDF5;border-color:#A7F3D0}
  .reg-info-box.gold{background:#FFFBEB;border-color:#FDE68A}
  .reg-info-icon{font-size:14px;line-height:1.4}
  .reg-info-text{font-size:12px;line-height:1.6;color:#334155}

  .form-card{
    background:#fff;border:1px solid var(--border);border-radius:14px;padding:18px;margin-bottom:14px;
  }
  .form-card-title{
    font-size:15px;font-weight:700;color:var(--dark);
    margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--border);
    display:flex;align-items:center;gap:8px;
  }
  .form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .form-group{display:flex;flex-direction:column;gap:5px}
  .form-group.full{grid-column:1/-1}
  .form-label{
    font-size:12px;font-weight:700;color:var(--gray);letter-spacing:.5px;text-transform:uppercase;
  }
  .req{color:var(--red)}
  .form-input,.form-select,.form-textarea{
    width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;
    padding:10px 12px;font-size:13px;font-family:var(--sans);color:var(--dark);outline:none;
    transition:all .2s;
  }
  .form-input:focus,.form-select:focus,.form-textarea:focus{
    border-color:var(--blue);background:#fff;box-shadow:0 0 0 3px rgba(26,86,219,.08);
  }
  .form-textarea{resize:vertical;min-height:84px}
  .form-hint{font-size:12px;color:#94A3B8}

  .vpath-box{
    background:var(--dark);border-radius:10px;padding:12px 14px;margin:10px 0;
    display:flex;align-items:center;gap:10px;
  }
  .vpath-label{font-size:12px;color:#475569;white-space:nowrap}
  .vpath-uri{font-family:var(--mono);font-size:12px;color:#60A5FA;font-weight:700;word-break:break-all;flex:1}
  .vpath-ok,.vpath-busy{
    font-size:12px;padding:2px 8px;border-radius:8px;white-space:nowrap;
  }
  .vpath-ok{color:#34D399;background:rgba(52,211,153,.1)}
  .vpath-busy{color:#F87171;background:rgba(248,113,113,.1)}
  .vpath-checking{color:#F59E0B;background:rgba(245,158,11,.14);font-size:12px;padding:2px 8px;border-radius:8px;white-space:nowrap}

  .seg-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
  .seg-opt{
    border:1.5px solid var(--border);border-radius:8px;padding:10px;text-align:center;
    cursor:pointer;transition:all .2s;background:#F8FAFC;
  }
  .seg-opt.sel{border-color:var(--blue);background:var(--blue-l)}
  .seg-opt-icon{font-size:20px;margin-bottom:4px}
  .seg-opt-name{font-size:12px;font-weight:700;color:var(--dark)}
  .seg-opt-desc{font-size:12px;color:var(--gray2);margin-top:2px}
  .seg-opt-info{font-size:12px;color:var(--blue);margin-top:4px;font-weight:600}
  .range-row{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center}
  .range-sep{font-size:14px;color:#94A3B8}

  .node-tree{
    background:var(--dark);border-radius:10px;padding:12px;
    font-family:var(--mono);font-size:12px;line-height:1.9;color:#60A5FA;
    max-height:190px;overflow-y:auto;
  }
  .node-tree-sub{padding-left:16px;color:#34D399}
  .node-tree-more{padding-left:16px;color:#475569}

  .perm-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
  .perm-card{
    border:1.5px solid var(--border);border-radius:10px;padding:12px;cursor:pointer;transition:all .2s;background:#fff;
  }
  .perm-card.sel{border-color:var(--blue);background:var(--blue-l)}
  .perm-icon{font-size:22px;margin-bottom:6px}
  .perm-name{font-size:13px;font-weight:700;color:var(--dark);margin-bottom:4px}
  .perm-desc{font-size:12px;color:var(--gray);line-height:1.5}
  .perm-roles{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
  .perm-role-tag{
    font-size:12px;padding:2px 6px;border-radius:4px;background:rgba(26,86,219,.12);
    color:var(--blue);font-weight:700;letter-spacing:.3px;
  }

  .btn-row{display:flex;gap:10px;margin-top:4px}
  .btn-primary,.btn-secondary{
    border-radius:10px;cursor:pointer;font-family:var(--sans);transition:all .2s;
  }
  .btn-primary{
    flex:1;padding:12px;background:var(--blue);color:#fff;border:none;font-size:14px;font-weight:700;
    box-shadow:0 4px 12px rgba(26,86,219,.3);
  }
  .btn-primary.btn-green{background:var(--green);box-shadow:0 4px 12px rgba(5,150,105,.25)}
  .btn-secondary{
    padding:12px 18px;background:#fff;color:var(--gray);border:1px solid var(--border);font-size:13px;
  }
  .btn-secondary:hover{border-color:var(--blue);color:var(--blue)}

  .success-banner{
    background:linear-gradient(135deg,#064E3B,#065F46);
    border-radius:14px;padding:24px;text-align:center;color:#fff;
  }
  .success-icon-big{
    width:60px;height:60px;border-radius:50%;background:rgba(52,211,153,.2);border:2px solid #34D399;
    display:flex;align-items:center;justify-content:center;font-size:26px;margin:0 auto 14px;
    animation:pop .35s cubic-bezier(.34,1.56,.64,1);
  }
  .success-uri{
    display:inline-block;margin:10px 0;padding:8px 16px;border-radius:8px;
    background:rgba(0,0,0,.2);color:#6EE7B7;font-family:var(--mono);font-size:13px;word-break:break-all;
  }

  .register-projects{
    background:#fff;border:1px solid var(--border);border-radius:14px;padding:16px;margin-top:14px;
  }
  .register-projects-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
  .register-projects-title{font-size:15px;font-weight:700;color:var(--dark)}
  .register-projects-count{font-size:12px;font-weight:700;background:var(--blue);color:#fff;padding:2px 8px;border-radius:999px}
  .register-project-list{display:grid;gap:8px}
  .reg-proj-card{
    border:1px solid var(--border);border-radius:10px;padding:10px;display:grid;
    grid-template-columns:auto 1fr auto;gap:10px;align-items:center;cursor:pointer;transition:all .2s;
  }
  .reg-proj-card:hover{border-color:#BFDBFE;background:#F8FAFF}
  .reg-proj-main{min-width:0}
  .reg-proj-name{font-size:13px;font-weight:700;color:var(--dark)}
  .reg-proj-uri{
    font-size:12px;font-family:var(--mono);color:var(--blue);margin-top:2px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  }
  .reg-proj-meta{font-size:12px;color:#64748B;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .reg-proj-actions{display:grid;gap:6px;justify-items:end}
  .register-empty{text-align:center;padding:34px 14px;color:#94A3B8}
  .register-empty-icon{font-size:34px;margin-bottom:8px}
  .register-empty-title{font-size:14px;font-weight:700;color:#64748B;margin-bottom:4px}
  .register-empty-sub{font-size:12px}

  .member-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
  .member-card{
    background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px;
    display:flex;flex-direction:column;gap:10px;transition:all .2s;
  }
  .member-card:hover{border-color:var(--blue);transform:translateY(-2px)}
  .member-header{display:flex;align-items:center;gap:10px}
  .member-avatar{
    width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    color:#fff;font-size:15px;font-weight:700;flex-shrink:0;
  }
  .member-name{font-size:14px;font-weight:700;color:var(--dark)}
  .member-title{font-size:12px;color:var(--gray);margin-top:2px}
  .role-badge{
    display:inline-block;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;
  }
  .role-owner{background:#EEF2FF;color:#4338CA}
  .role-supervisor{background:var(--blue-l);color:var(--blue)}
  .role-inspector{background:var(--green-l);color:var(--green)}
  .role-viewer{background:var(--bg);color:var(--gray)}
  .member-projects{font-size:12px;color:var(--gray);background:var(--bg);padding:6px 10px;border-radius:6px}
  .member-actions{display:flex;gap:6px;flex-wrap:wrap}

  .perm-toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
  .perm-layout{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:18px;align-items:start}
  .perm-table{width:100%;border-collapse:collapse;font-size:12px}
  .perm-table th{
    text-align:left;padding:8px 10px;border-bottom:1px solid var(--border);color:#64748B;background:#F8FAFC;
  }
  .perm-table td{padding:9px 10px;border-bottom:1px solid #F1F5F9}
  .perm-role{
    font-family:var(--mono);font-size:12px;font-weight:700;padding:2px 8px;border-radius:4px;
    color:var(--blue);background:rgba(26,86,219,.12);
  }
  .perm-role-owner{background:#DBEAFE;color:#1D4ED8}
  .perm-role-supervisor{background:#D1FAE5;color:#065F46}
  .perm-role-ai{background:#FEF3C7;color:#92400E}
  .perm-role-public{background:#F3F4F6;color:#374151}
  .perm-role-regulator{background:#FCE7F3;color:#BE185D}
  .perm-role-market{background:#ECFEFF;color:#0E7490}

  .settings-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .settings-section{
    background:#fff;border:1px solid var(--border);border-radius:14px;padding:18px;
  }
  .settings-title{
    font-size:14px;font-weight:700;color:var(--dark);margin-bottom:14px;padding-bottom:10px;
    border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;
  }
  .toggle-row{
    display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);gap:10px;
  }
  .toggle-row:last-child{border-bottom:none}
  .toggle-label{font-size:13px;color:var(--text)}
  .setting-input,.setting-select{
    width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;font-family:var(--sans);
  }
  .setting-note{
    padding:10px;border:1px solid var(--border);border-radius:8px;background:#F8FAFF;font-size:12px;color:#64748B;
  }

  .invite-mask{
    position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;align-items:center;justify-content:center;z-index:999;
  }
  .invite-panel{
    width:420px;max-width:92vw;background:#fff;border-radius:12px;padding:16px;
  }
  .invite-title{font-size:16px;font-weight:700;margin-bottom:10px}
  .invite-form{display:grid;gap:8px}
  .invite-row{display:flex;gap:8px;margin-top:12px}

  @media(max-width:768px){
    .sidebar{transform:translateX(-100%)}
    .sidebar.open{transform:translateX(0)}
    .main-content{margin-left:0}
    .dash-stats{grid-template-columns:repeat(2,1fr)}
    .dash-grid{grid-template-columns:1fr}
    .form-grid,.settings-grid{grid-template-columns:1fr}
    .perm-grid{grid-template-columns:1fr}
    .perm-layout{grid-template-columns:1fr}
    .reg-steps{display:grid;grid-template-columns:1fr 1fr}
    .register-title{font-size:22px}
    .register-hero-stats{gap:16px}
    .reg-proj-card{grid-template-columns:1fr}
    .reg-proj-actions{justify-items:start}
  }
  @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  @keyframes pop{from{transform:scale(0)}to{transform:scale(1)}}
`
document.head.appendChild(style)

ReactDOM.createRoot(document.getElementById('root')!).render(
  window.location.pathname.startsWith('/v/') ? <PublicVerifyPage /> : <App />
)


