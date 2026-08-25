#!/usr/bin/env python3
"""Add compact percentage labels to the largest Asset Allocation donut slices."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

CSS = r'''.donut-label{position:absolute;left:50%;top:50%;z-index:2;transform:translate(-50%,-50%);font-size:11px;font-weight:800;color:#fff;text-shadow:0 1px 4px #000,0 0 2px #000;pointer-events:none;white-space:nowrap}.donut:after{z-index:1}.donut{overflow:visible}'''

NEW_FUNC = r'''function donut(el,legend,rows,total,showMajorLabels=false){
 const node=document.getElementById(el);let start=0;
 const seg=rows.map((x,i)=>{const a=360*x.value/total;const s=`${colors[i%colors.length]} ${start}deg ${start+a}deg`;start+=a;return s});
 node.style.background=`conic-gradient(${seg.join(',')})`;
 node.querySelectorAll('.donut-label').forEach(n=>n.remove());
 if(showMajorLabels){
   let angle=0;
   rows.forEach((x,i)=>{
     const share=x.value/total,a=360*share,mid=angle+a/2;angle+=a;
     if(share<.08||i>=5)return;
     const r=38,rad=(mid-90)*Math.PI/180;
     const label=document.createElement('span');label.className='donut-label';label.textContent=pct.format(share);
     label.style.marginLeft=`${Math.cos(rad)*r}%`;label.style.marginTop=`${Math.sin(rad)*r}%`;node.appendChild(label);
   });
 }
 document.getElementById(legend).innerHTML=rows.map((x,i)=>`<div class="legend-row"><span class="dot" style="background:${colors[i%colors.length]}"></span><span>${x.name}</span><b>${pct.format(x.value/total)}</b></div>`).join('');
}'''

def main():
    text = INDEX.read_text(encoding="utf-8")
    if ".donut-label{" not in text:
        text = text.replace("</style>", CSS + "\n</style>", 1)
    pattern = re.compile(r"function donut\(el,legend,rows,total\)\{.*?\}\n(?=donut\('assetDonut')", re.S)
    if not pattern.search(text):
        # Allow reruns after this script has already installed the enhanced signature.
        pattern = re.compile(r"function donut\(el,legend,rows,total,showMajorLabels=false\)\{.*?\}\n(?=donut\('assetDonut')", re.S)
    if not pattern.search(text):
        raise ValueError("Could not locate donut renderer")
    text = pattern.sub(NEW_FUNC + "\n", text, count=1)
    text = text.replace("donut('assetDonut','assetLegend',DATA.assets,DATA.meta.total);", "donut('assetDonut','assetLegend',DATA.assets,DATA.meta.total,true);")
    INDEX.write_text(text, encoding="utf-8")
    print("Added percentage labels for the largest Asset Allocation donut slices (>=8%, max 5).")

if __name__ == "__main__":
    main()
