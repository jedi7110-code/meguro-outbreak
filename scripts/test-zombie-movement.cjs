const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
const source = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
new Function(source);
function extract(name) {
  const start = source.indexOf('function ' + name + '(');
  const end = source.indexOf('\n    function ', start + 1);
  return source.slice(start, end);
}
const context = vm.createContext({assert});
vm.runInContext(`
  const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
  const graph={nodes:new Map([['a',[0,0]],['b',[100,0]],['c',[100,100]]]),adj:new Map([['a',[['b',100]]],['b',[['a',100],['c',100]]],['c',[['b',100]]]])};
  let player={pos:[100,0]}, zombies=[],lastHit=0,health=100;
  const document={body:{classList:{add(){},remove(){}}}};
  function setTimeout(){} function finish(){}
  ${extract('nearest')}
  ${extract('route')}
  ${extract('moveToward')}
  ${extract('updateZombies')}
  function simulate(pos,target){
    player.pos=target;health=100;lastHit=0;
    const z={pos:[...pos],path:[],step:0,nextThink:0,marker:{setLatLng(){}}};
    zombies=[z];
    for(let now=50;now<=30000;now+=50){
      updateZombies(.05,now);
      assert(z.pos[1]===0||z.pos[0]===100,'must follow the road around the corner');
    }
    assert(dist(z.pos,target)<.4,'zombie must reach the destination');
    assert(health<100,'zombie must enter attack range');
  }
  simulate([60,0],[100,0]); // Nearest node is already the goal, 40m ahead.
  simulate([0,0],[100,100]); // Replanning must preserve the junction.
`, context);
console.log('PASS: goal-node approach, junction movement, and attack range');
