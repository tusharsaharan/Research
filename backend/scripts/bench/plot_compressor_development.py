"""Export scientific figures directly from saved development analysis artifacts."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from compressor_artifacts import digest,save


def plot(report_path,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    report=json.loads(report_path.read_text())
    if report['status']!='complete':raise ValueError('Only complete analyses can be plotted')
    output.mkdir(parents=True,exist_ok=True)
    names={'original':'Original','no_context':'No context','teacher_prefix':'Teacher prefix',
        'teacher_atomic':'Teacher atomic','student_atomic':'Lexical student','student_neural':'Neural student',
        'bm25_atomic':'BM25 atomic','shuffled':'Shuffled','llml2_strict':'LLMLingua-2','xprovence_strict':'XProvence'}
    colors=dict(zip(names,['#202020','#888888','#1d70b8','#003d6b','#e87500','#00845a','#6a492f','#a4a400','#844aa4','#cb3b70']))
    fig,axes=plt.subplots(1,2,figsize=(12,5.5),sharey=True)
    labelled=set()
    for method,metric in report['metrics'].items():
        base=method.split('@')[0];marker='o' if method.endswith('@0.5') else 's' if '@' in method else 'D'
        label=names[base] if base not in labelled else None;labelled.add(base)
        axes[0].scatter(metric['context_retention'],100*metric['accuracy'],color=colors[base],marker=marker,s=55,label=label)
        seconds=metric['compression_plus_generation_seconds_mean']
        if seconds is not None:axes[1].scatter(seconds,100*metric['accuracy'],color=colors[base],marker=marker,s=55)
        if base in ['original','no_context','student_neural']:
            text=names[base]+(' '+method.split('@')[1] if '@' in method else '')
            for ax,x in [(axes[0],metric['context_retention']),(axes[1],seconds)]:
                if x is not None:ax.annotate(text,(x,100*metric['accuracy']),xytext=(4,6),textcoords='offset points',fontsize=8)
    axes[0].set(xlabel='Actual context tokens kept / original context tokens',ylabel='QA accuracy (%)',xlim=(-.05,1.10),ylim=(0,100))
    axes[1].set(xlabel='Compression + generation component seconds / query')
    for ax in axes:ax.grid(alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Native Mistral: exposed development, 183 questions / 97 passages',fontsize=12)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=5,fontsize=8,frameon=False)
    fig.text(.5,.11,'Circles: 0.50 budget; squares: 0.33. Timings include reused component measurements and historical teacher ranking; not serving throughput.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.15,1,.95))
    for suffix in ['png','svg']:fig.savefig(output/('native_tradeoff.'+suffix),dpi=180,bbox_inches='tight')
    plt.close(fig)
    selected=[r for r in report['comparisons'] if r['candidate'].startswith(('student_atomic@','student_neural@'))]
    fig,ax=plt.subplots(figsize=(10,max(4,len(selected)*.42)))
    labels=[]
    for i,row in enumerate(selected):
        center=100*row['delta'];low,high=[100*v for v in row['ci95']]
        base,rate=row['candidate'].split('@');baseline=row['baseline'].split('@')[0]
        ax.errorbar(center,i,xerr=[[center-low],[high-center]],fmt='o',color=colors[base],capsize=3)
        labels.append(f"{names[base]} {rate} vs {names[baseline]}   (Holm p={row['holm_p_all_comparisons']:.3f})")
    ax.axvline(0,color='#444444',linestyle='--',linewidth=1)
    ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    ax.set_xlabel('Candidate minus baseline accuracy (percentage points)')
    ax.set_title('Paired passage-bootstrap 95% intervals: exploratory, unadjusted intervals',fontsize=11)
    fig.tight_layout()
    for suffix in ['png','svg']:fig.savefig(output/('native_student_differences.'+suffix),dpi=180,bbox_inches='tight')
    plt.close(fig)
    save(output/'figure_manifest.json',dict(source_report_sha256=digest(report_path),script_sha256=digest(Path(__file__)),
        files={p.name:digest(p) for p in output.iterdir() if p.suffix in ['.png','.svg']},
        scope='Exposed development; all comparisons and exact uncertainty are in the source report. No confirmatory claim.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();plot(a.report,a.output)
