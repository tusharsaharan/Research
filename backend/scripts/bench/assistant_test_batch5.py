"""Independent test solutions 2030/A-D."""
import json
from pathlib import Path
ANSWERS=[
('2030/A','The first prefix has range zero; each later prefix has range at most max(a)-min(a). Put the global minimum and maximum first to attain that bound for all n-1 later prefixes. Answer (n-1)*(max-min). O(n) time, O(1) auxiliary space.',r'''#include <bits/stdc++.h>
using namespace std;int main(){int t;cin>>t;while(t--){int n;cin>>n;int lo=INT_MAX,hi=INT_MIN;for(int i=0,x;i<n;i++){cin>>x;lo=min(lo,x);hi=max(hi,x);}cout<<1LL*(n-1)*(hi-lo)<<'\n';}}'''),
('2030/B','With z zeros, f=2^z-1 and g=2^n-2^z, so the difference is |2^(z+1)-2^n-1|. For z=n-1 it is 1; a zero difference is impossible since the difference is odd. Output one 1 and n-1 zeros. O(n) time and output memory.',r'''#include <bits/stdc++.h>
using namespace std;int main(){ios::sync_with_stdio(false);cin.tie(nullptr);int t;cin>>t;while(t--){int n;cin>>n;cout<<'1'<<string(n-1,'0')<<'\n';}}'''),
('2030/C','Alice wins precisely if an endpoint is 1 or there are adjacent 1s. An endpoint 1 needs only its one boundary protected by OR. For adjacent 1s Alice places OR between them, then can protect the surviving boundary after Bob attacks one side. Otherwise every 1 is isolated between zeros; Bob responds whenever Alice tries to protect one side by placing AND on its other side, killing that singleton. Independent isolated ones can all be handled this way, while Alice gains nothing by placing AND. Scan for these patterns. O(n) time, O(1) extra space.',r'''#include <bits/stdc++.h>
using namespace std;int main(){ios::sync_with_stdio(false);cin.tie(nullptr);int t;cin>>t;while(t--){int n;string s;cin>>n>>s;bool win=s.front()=='1'||s.back()=='1'||s.find("11")!=string::npos;cout<<(win?"YES":"NO")<<'\n';}}'''),
('2030/D','Boundary i between i and i+1 is blocked only for pattern LR. Sorting is possible iff every blocked boundary already separates the correct sets of values, equivalently max(p[1..i])=i. Precompute which boundaries require crossing. Maintain the count of required-but-blocked boundaries. Toggling position x only changes boundaries x-1 and x; subtract their old contributions, toggle, add new. Answer YES iff count zero. O(n+q) time, O(n) memory.',r'''#include <bits/stdc++.h>
using namespace std;int main(){ios::sync_with_stdio(false);cin.tie(nullptr);int t;cin>>t;while(t--){int n,q;cin>>n>>q;vector<int>need(n);int mx=0;for(int i=0,x;i<n;i++){cin>>x;mx=max(mx,x);need[i]=mx>i+1;}string s;cin>>s;auto bad=[&](int i){return i>=0&&i+1<n&&need[i]&&s[i]=='L'&&s[i+1]=='R';};int cnt=0;for(int i=0;i+1<n;i++)cnt+=bad(i);while(q--){int x;cin>>x;--x;cnt-=bad(x-1)+bad(x);s[x]=(s[x]=='L'?'R':'L');cnt+=bad(x-1)+bad(x);cout<<(cnt?"NO":"YES")<<'\n';}}}''')]
if __name__=='__main__':
    p=Path('backend/data/bench/codeforces700_20261116/assistant_answers_v1/shard_test_000_199.jsonl')
    with p.open('a',encoding='utf-8') as out:
        for ident,explanation,code in ANSWERS:
            out.write(json.dumps({'id':ident,'split':'test','author':'current chat assistant','status':'authored','explanation':explanation,'cpp_code':code,'validation':'not executed'})+'\n')
