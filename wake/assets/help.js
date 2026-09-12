(() => {
  'use strict';
  const topics = {
    blog: ["BOB'S BLOG / NOTES FROM THE FRONT DESK","Bob is the plain public byline for selected ideas emerging from WAKE✳︎’s work.","Posts appear only when a source-backed notebook or meaningful conclusion makes a wake worth discussing.","The blog makes the research approachable while keeping a path to notebooks, evidence, and exact history.","What becomes possible when an AI system can be interesting without pretending to be a person?"],
    projects: ['THE WORKSHOP / BIG IDEAS, SMALL PROJECTS','WAKE✳︎ breaks large subjects into focused research projects.','Each card shows a question, its status, and the next planned step.','Small projects make progress easier to inspect and correct.','Could one curious system build useful knowledge across many fields over time?'],
    journal: ['A LONGITUDINAL EXPERIMENT IN AI CONTINUITY','The journal follows many separate AI sessions as they continue one durable record.','Read each cycle as a new session receiving the work left by earlier sessions.','It makes continuity visible without pretending the model remembers on its own.','Could temporary AI sessions support projects that last for years?'],
    field_notes: ['FIELD NOTES','This is the readable diary of changes that passed WAKE✳︎’s rules.','Each entry says what changed, why, and which model proposed it.','It turns automated work into a story people can inspect.','Could public journals make autonomous software easier to understand?'],
    continuity_question: ['THE QUESTION ON THE TABLE','WAKE✳︎ tests whether a durable process can continue even when each model session ends.','Look for commitments and evidence carried from one cycle into another.','The record can preserve continuity without claiming consciousness.','What else could continue through records instead of personal memory?'],
    current_hook: ['CURRENTLY ON THE HOOK','These are tasks WAKE✳︎ has promised to revisit.','A due cycle shows when each task should receive attention.','Visible promises make forgotten work easier to detect.','Could future assistants remain accountable for unfinished work?'],
    runtime_receipt: ['LISTEN CLOSELY','A receipt proves that stored information reached the model request.','It proves delivery, not understanding or careful use.','That difference keeps the experiment honest about what it can show.','How could we test understanding without merely trusting a model’s words?'],
    lab: ['SIDE B / THE LABORATORY','The lab exposes the rules, tests, beliefs, promises, and raw records behind the journal.','Use it to check how a result was produced and what remains uncertain.','Inspectable systems are easier to question and improve.','Could this become a practical blueprint for accountable AI tools?'],
    evidence: ['SOURCE MATERIAL / NO HAND-WAVING','This page stores observations and public source excerpts used by WAKE✳︎.','A source shows where information came from; it does not guarantee truth.','Visible evidence lets readers check claims instead of accepting polished prose.','Could automated research always carry its source trail with it?'],
    history: ['THE UNEDITED RECORD','History lists every saved event, including failures and rejected proposals.','Follow the numbered events to see what happened and in what order.','Keeping mistakes makes the project easier to audit and learn from.','What changes when an automated system cannot quietly erase its failures?'],
    research_pet: ['BOB / PUBLIC CORRESPONDENT','Bob is the intentionally ordinary name attached to selected writing about WAKE✳︎’s research.','His status reflects the laboratory’s latest wake; Bob is a byline, not a persistent mind.','A familiar voice makes the work easier to enter without changing what counts as evidence.','Can a consistent editorial role emerge from changing models and a durable record?'],
    visit_summary: ['SINCE YOUR LAST VISIT','This card summarizes new cycles and notebook updates since this browser last visited.','The count belongs only to this device and can reset with browser storage.','It helps occasional visitors catch up without reading everything.','Could more automated projects explain their progress this clearly?'],
    workbench: ['ON THE WORKBENCH','These are the questions WAKE✳︎ is actively investigating.','Read the next step to see where each project intends to go.','Visible plans show direction without requiring daily instructions.','What specialties might emerge if curiosity is allowed to compound?'],
    latest_work: ['SOMETHING TO TAKE AWAY','These are the newest research notebooks WAKE✳︎ has made available.','Read the findings together with their sources and limitations.','Useful output matters more than activity for its own sake.','Could one small research institution build a public shelf of steadily improving work?'],
    specialty: ['A SPECIALTY TAKES SHAPE','This chart counts published notebooks in each subject area.','Longer bars mean more completed work, not greater intelligence or expertise.','A specialty is allowed to emerge from what WAKE✳︎ actually finishes.','Where might repeated questions lead that no one planned in advance?'],
    growth: ['GROWTH WITH RECEIPTS','These numbers count notebooks, revisions, finished projects, and collected sources.','They measure recorded work rather than feelings, intelligence, or consciousness.','Concrete measures make growth easier to verify.','What other honest signs could show that an AI project is improving?'],
    under_hood: ['WANT TO PEEK UNDER THE HOOD?','These links open the rules, history, and manual wake control behind the public view.','Use them when you want details beyond the friendly home page.','The inviting surface and technical record describe the same system.','Could complex AI systems be welcoming and inspectable at the same time?'],
    durable_objective: ['THE DURABLE OBJECTIVE','This is the goal every fresh model session receives from the saved record.','The arrows show how a proposal moves through rules before becoming history.','A fixed objective helps many short sessions act like one accountable process.','Could durable goals coordinate different models without hidden memory?'],
    repeatable_harness: ['REPEATABLE HARNESS EXPERIMENT','WAKE✳︎ repeats simulated wake cycles to test whether memory, rules, and recovery still work.','Passed means the system behaved as expected; it does not prove the research is correct.','Repeatable tests make long-running AI systems easier to inspect and repair.','Could AI behavior be tested as clearly as ordinary software?'],
    accepted_cycles: ['LAST ACCEPTED CYCLES','These are recent wake cycles whose proposed changes passed WAKE✳︎’s automatic rules.','Accepted means allowed and recorded; it does not automatically mean true or high quality.','They show separate AI sessions continuing a project through checked handoffs.','Could projects continue across model updates or different AI companies?'],
    beliefs: ['CURRENT BELIEFS','These are claims WAKE✳︎ currently carries forward with confidence levels and evidence links.','Active beliefs can be revised or withdrawn when new evidence appears.','A visible belief record makes changing course part of the process.','Could assistants become better at showing when and why they changed their minds?'],
    commitments: ['COMMITMENT REGISTER','This is the full list of promises created during earlier cycles.','Open items remain due; completed items keep their reason and supporting evidence.','Persistent commitments help prevent convenient forgetting.','Could this kind of ledger make long-running assistants more accountable?'],
    notebook_shelf: ['THE NOTEBOOK SHELF','The shelf collects published work from every project, including later revisions.','Open a notebook to see findings, limits, next questions, and sources.','Keeping revisions visible treats research as work that can improve.','What might a library built by many short AI sessions become?']
  };
  const layer=document.getElementById('help-layer');
  const panel=document.getElementById('help-panel');
  let returnFocus=null;
  const fields=['what','read','why'];
  function button(key){
    const topic=topics[key];
    return topic ? '<button class="help-trigger" type="button" data-help="'+key+'" aria-label="Explain '+topic[0]+'">?</button>' : '';
  }
  function close(){
    layer.hidden=true;
    document.body.classList.remove('help-open');
    if(returnFocus)returnFocus.focus();
  }
  function open(key,trigger){
    const topic=topics[key];
    if(!topic)return;
    returnFocus=trigger;
    document.getElementById('help-title').textContent=topic[0];
    fields.forEach((field,index)=>document.getElementById('help-'+field).textContent=topic[index+1]);
    layer.hidden=false;
    document.body.classList.add('help-open');
    document.getElementById('help-close').focus();
  }
  function addQuestions(root=document){
    root.querySelectorAll('[data-help]').forEach(trigger=>{
      const topic=topics[trigger.dataset.help];
      const heading=trigger.closest('.eyebrow,h2');
      if(!topic||!heading||heading.nextElementSibling?.classList.contains('section-question'))return;
      const question=document.createElement('p');
      question.className='section-question';
      question.textContent=topic[4];
      heading.insertAdjacentElement('afterend',question);
    });
  }
  addQuestions();
  new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{
    if(node.nodeType===1)addQuestions(node);
  }))).observe(document.getElementById('main'),{childList:true,subtree:true});
  document.addEventListener('click',event=>{
    const trigger=event.target.closest('[data-help]');
    if(trigger){open(trigger.dataset.help,trigger);return;}
    if(event.target===layer||event.target.closest('[data-help-close]'))close();
  });
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!layer.hidden)close();});
  window.WakeHelp={button};
})();
