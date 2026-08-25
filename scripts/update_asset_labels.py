#!/usr/bin/env python3
"""Add readable external labels and hover tooltips to both dashboard donut charts."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

CSS = r'''/* donut-callouts-v2 */
.pie{min-height:390px;overflow:visible}
.donut{width:100%;max-width:650px;height:380px;border-radius:0;position:relative;background:none!important;overflow:visible}
.donut:after{display:none}
.donut svg{width:100%;height:100%;overflow:visible}
.donut-segment{cursor:help;transition:filter .12s,stroke-width .12s}
.donut-segment:hover{filter:brightness(1.18);stroke:#fff;stroke-width:1.5}
.donut-callout{pointer-events:none}
.donut-callout text{fill:#eef2ff;font-size:11px}
.donut-callout .pct-label{font-weight:800}
.donut-callout .name-label{fill:#cbd5e1;font-size:10px}
@media(max-width:650px){.pie{min-height:360px}.donut{height:350px;max-width:100%}.donut-callout text{font-size:10px}.donut-callout .name-label{font-size:9px}}
'''

NEW_FUNC = r'''function donut(el,legend,rows,total){
 const host=document.getElementById(el),W=650,H=380,cx=W/2,cy=H/2,ro=108,ri=62;
 const safeTotal=Number(total)||rows.reduce((s,x)=>s+Number(x.value||0),0)||1;
 const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
 const polar=(r,a)=>({x:cx+r*Math.cos(a),y:cy+r*Math.sin(a)});
 const arc=(a0,a1)=>{const p0=polar(ro,a0),p1=polar(ro,a1),q1=polar(ri,a1),q0=polar(ri,a0),large=(a1-a0)>Math.PI?1:0;return `M ${p0.x} ${p0.y} A ${ro} ${ro} 0 ${large} 1 ${p1.x} ${p1.y} L ${q1.x} ${q1.y} A ${ri} ${ri} 0 ${large} 0 ${q0.x} ${q0.y} Z`;};
 let angle=-Math.PI/2;
 const segs=rows.map((x,i)=>{const a0=angle,a1=angle+Math.PI*2*Number(x.value||0)/safeTotal,mid=(a0+a1)/2;angle=a1;return {...x,i,a0,a1,mid,share:Number(x.value||0)/safeTotal};});
 const top=new Set([...segs].sort((a,b)=>b.value-a.value).slice(0,8).map(x=>x.i));
 const calls=segs.filter(x=>top.has(x.i)).map(x=>{const edge=polar(ro+4,x.mid);return {...x,edge,side:Math.cos(x.mid)>=0?'r':'l',ideal:edge.y};});
 for(const side of ['l','r']){
  const arr=calls.filter(x=>x.side===side).sort((a,b)=>a.ideal-b.ideal),minY=42,maxY=338,gap=36;
  arr.forEach((x,j)=>x.ly=Math.max(minY,x.ideal,j?arr[j-1].ly+gap:minY));
  for(let j=arr.length-2;j>=0;j--)arr[j].ly=Math.min(arr[j].ly,arr[j+1].ly-gap);
  if(arr.length&&arr[arr.length-1].ly>maxY){const shift=arr[arr.length-1].ly-maxY;arr.forEach(x=>x.ly-=shift);}
 }
 const paths=segs.map(x=>`<path class="donut-segment" d="${arc(x.a0,x.a1)}" fill="${colors[x.i%colors.length]}" stroke="#141b2d" stroke-width="1"><title>${esc(x.name)} · ${pct.format(x.share)}</title></path>`).join('');
 const callouts=calls.map(x=>{const elbow=polar(ro+26,x.mid),tx=x.side==='r'?W-18:18,ex=x.side==='r'?W-118:118,anchor=x.side==='r'?'end':'start';return `<g class="donut-callout"><polyline points="${x.edge.x},${x.edge.y} ${elbow.x},${elbow.y} ${ex},${x.ly}" fill="none" stroke="${colors[x.i%colors.length]}" stroke-width="1.4"/><text x="${tx}" y="${x.ly-3}" text-anchor="${anchor}"><tspan class="pct-label">${pct.format(x.share)}</tspan><tspan class="name-label" x="${tx}" dy="14">${esc(x.name)}</tspan></text></g>`}).join('');
 host.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${el==='assetDonut'?'Asset Allocation':'Branchenanteile'} mit Beschriftungen der acht größten Segmente">${paths}${callouts}</svg>`;
 document.getElementById(legend).innerHTML=rows.map((x,i)=>`<div class="legend-row"><span class="dot" style="background:${colors[i%colors.length]}"></span><span>${x.name}</span><b>${pct.format(Number(x.value||0)/safeTotal)}</b></div>`).join('');
}'''


def main():
    text = INDEX.read_text(encoding="utf-8")
    text = re.sub(r'/\* donut-callouts-v2 \*/.*?(?=</style>)', '', text, flags=re.S)
    text = re.sub(r'\.donut-label\{.*?\}(?=</style>|\n)', '', text, flags=re.S)
    text = text.replace('</style>', CSS + '\n</style>', 1)
    pattern = re.compile(r"function donut\(el,legend,rows,total(?:,showMajorLabels=false)?\)\{.*?\}\n(?=donut\('assetDonut')", re.S)
    if not pattern.search(text):
        raise ValueError("Could not locate donut renderer")
    text = pattern.sub(NEW_FUNC + "\n", text, count=1)
    text = text.replace("donut('assetDonut','assetLegend',DATA.assets,DATA.meta.total,true);", "donut('assetDonut','assetLegend',DATA.assets,DATA.meta.total);")
    text = re.sub(r"donut\('sectorDonut','sectorLegend',DATA\.sectors\.slice\(0,10\),DATA\.sectors\.slice\(0,10\)\.reduce\(\(a,b\)=>a\+b\.value,0\)\);", "donut('sectorDonut','sectorLegend',DATA.sectors,DATA.meta.total);", text, count=1)
    INDEX.write_text(text, encoding="utf-8")
    print("Added external name + percentage labels for the 8 largest Asset Allocation and sector slices, plus hover tooltips for every slice.")


if __name__ == "__main__":
    main()
