const runs=[
 {id:'support-20260912-018',agent:'support-resolution',time:'10:41 UTC',status:'completed',events:18},
 {id:'checkout-20260912-017',agent:'checkout-assistant',time:'10:12 UTC',status:'completed',events:22},
 {id:'support-20260912-016',agent:'support-resolution',time:'09:55 UTC',status:'failed',events:9},
 {id:'policy-20260911-044',agent:'policy-reviewer',time:'17:09 UTC',status:'completed',events:14}
];
const stream=[
 ['00','state','run started','session: cs_8492 · schema v1','10:41:02.031Z',{kind:'run_started',run_id:'support-20260912-018',sequence:0,payload:{agent:'support-resolution',session_id:'cs_8492'}}],
 ['01','model','model request','call_id: model-001 · 2 messages','10:41:02.118Z',{kind:'model_request',call_id:'model-001',payload:{messages:[{role:'system',content:'Use verified evidence only.'},{role:'user',content:'Where is order #9842?'}]}}],
 ['02','model','model response','call_id: model-001 · 48 tokens','10:41:03.992Z',{kind:'model_response',call_id:'model-001',payload:{content:'I will look up the order status.'}}],
 ['03','tool','tool request','order_lookup · order_id: ORD-9842','10:41:04.101Z',{kind:'tool_request',call_id:'tool-014',payload:{tool_name:'order_lookup',arguments:{order_id:'ORD-9842'}}}],
 ['04','tool','tool response','order_lookup · status: delayed','10:41:04.428Z',{kind:'tool_response',call_id:'tool-014',payload:{order_id:'ORD-9842',status:'delayed',carrier:'ParcelPost',eta:'2026-09-14'}}],
 ['05','state','state delta','case.status → carrier_delay','10:41:04.433Z',{kind:'state_delta',payload:{path:'case.status',from:'open',to:'carrier_delay'}}],
 ['06','model','model request','call_id: model-002 · 3 messages','10:41:04.519Z',{kind:'model_request',call_id:'model-002',payload:{messages:[{role:'system',content:'Use verified evidence only.'},{role:'tool',content:'Order delayed by carrier.'},{role:'user',content:'Explain next step.'}]}}],
 ['07','model','model response','call_id: model-002 · 66 tokens','10:41:06.310Z',{kind:'model_response',call_id:'model-002',payload:{content:'Your order is delayed with ParcelPost and is expected by September 14.'}}],
 ['08','state','run completed','terminal: success','10:41:06.428Z',{kind:'run_completed',payload:{answer:'Carrier delay explanation returned.',exchanges_consumed:2}}]
];
let active=0, selected=4;const byId=id=>document.getElementById(id);
function renderRuns(){byId('runItems').innerHTML=runs.map((r,i)=>`<button class="run ${i===active?'active':''}" data-run="${i}"><b>${r.id}</b><small><i>●</i> ${r.agent} · ${r.events} events</small><small>${r.time} · ${r.status}</small></button>`).join('');document.querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>{active=+b.dataset.run;byId('selectedRun').textContent=runs[active].id;byId('timelineTitle').textContent=runs[active].id;byId('eventCount').textContent=runs[active].events;renderRuns()})}
function renderEvents(){byId('events').innerHTML=stream.map((e,i)=>`<button class="event ${e[1]} ${i===selected?'active':''}" data-event="${i}"><span class="event-num">${e[0]}</span><span class="event-line"></span><span class="event-copy"><b>${e[2]}</b><small>${e[3]}</small></span><time>${e[4].slice(0,8)}</time></button>`).join('');document.querySelectorAll('[data-event]').forEach(b=>b.onclick=()=>{selected=+b.dataset.event;renderEvents();renderDetail()})}
function renderDetail(){const e=stream[selected];byId('detailTitle').textContent=e[2];byId('eventSeq').textContent=`sequence ${e[0]}`;byId('eventTime').textContent=e[4];byId('eventJson').textContent=JSON.stringify(e[5],null,2)}
renderRuns();renderEvents();renderDetail();
const dialog=byId('replayDialog');byId('replayBtn').onclick=()=>dialog.showModal();byId('closeDialog').onclick=()=>dialog.close();byId('confirmReplay').onclick=()=>{byId('dialogTitle').textContent='Replay completed';byId('dialogCopy').textContent='9 recorded exchanges matched. No external model or tool calls were made.';byId('confirmReplay').disabled=true;byId('confirmReplay').textContent='Completed'};byId('compareBtn').onclick=()=>document.querySelector('#diff').scrollIntoView({behavior:'smooth'});byId('viewDiffBtn').onclick=()=>{selected=3;renderEvents();renderDetail();document.querySelector('#runs').scrollIntoView({behavior:'smooth'})};byId('copyBtn').onclick=()=>navigator.clipboard?.writeText(byId('eventJson').textContent);byId('themeBtn').onclick=()=>document.body.classList.toggle('high-contrast');
