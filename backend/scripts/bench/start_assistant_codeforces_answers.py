"""Persist this chat assistant's independently authored first three answers."""
import hashlib
import json
from pathlib import Path

ROOT = Path('backend/data/bench/codeforces700_20261116')
OUT = ROOT / 'assistant_answers_v1'

ANSWERS = {
'852/C': ('''Let x[i] be the court's fraction along even edge i and y[i] Bill's fraction along the next edge. The removed corner areas adjacent to y[i] are proportional to (1-x[i])*y[i] + (1-y[i])*x[i+1]. Their y-dependent term is y[i]*(1-x[i]-x[i+1]). Thus minimize total removed area by pairing increasing y with increasing x[i]+x[i+1]. An exchange of two assignments proves this: assigning the larger y to the larger sum never increases removed area. Sort indices by the sum of adjacent court indices and assign 0 through n-1 in that order. O(n log n) time, O(n) memory.''', r'''#include <bits/stdc++.h>
using namespace std;
int main(){ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;cin>>n;vector<int>a(n),order(n),ans(n);for(int &x:a)cin>>x;
 iota(order.begin(),order.end(),0);
 sort(order.begin(),order.end(),[&](int i,int j){return a[i]+a[(i+1)%n]<a[j]+a[(j+1)%n];});
 for(int k=0;k<n;k++)ans[order[k]]=k;
 for(int i=0;i<n;i++)cout<<ans[i]<<(i+1==n?'\n':' ');
}'''),
'852/D': ('''Compute shortest distances from each team start with Dijkstra. For a candidate time T, build a bipartite graph from teams to cities, connecting a team to every city reachable within T. A matching of size at least K is necessary and sufficient: choose one representative team for each distinct final city; conversely the matched teams achieve K cities and all others can stay at their starts. Use augmenting-path matching, stopping at K. Feasibility is monotone, so binary-search sorted finite distance values. Complexity O(N*(E+V)*log V + N*N*V*log(N*V)) time and O(N*V+E) space. All arithmetic distances use long long.''', r'''#include <bits/stdc++.h>
using namespace std;using ll=long long;
int main(){ios::sync_with_stdio(false);cin.tie(nullptr);
 int V,E,N,K;cin>>V>>E>>N>>K;vector<int>s(N);for(int &x:s){cin>>x;--x;}
 vector<vector<pair<int,int>>>g(V);for(int i=0,u,v,w;i<E;i++){cin>>u>>v>>w;--u;--v;g[u].push_back({v,w});g[v].push_back({u,w});}
 const ll INF=1LL<<60;vector<vector<ll>>d(N,vector<ll>(V,INF));vector<ll>values{0};
 for(int i=0;i<N;i++){priority_queue<pair<ll,int>,vector<pair<ll,int>>,greater<pair<ll,int>>>pq;d[i][s[i]]=0;pq.push({0,s[i]});
 while(!pq.empty()){ll du=pq.top().first;int u=pq.top().second;pq.pop();if(du!=d[i][u])continue;for(auto edge:g[u]){int v=edge.first,w=edge.second;if(du+w<d[i][v]){d[i][v]=du+w;pq.push({d[i][v],v});}}}
 for(ll x:d[i])if(x<INF)values.push_back(x);}
 sort(values.begin(),values.end());values.erase(unique(values.begin(),values.end()),values.end());
 auto feasible=[&](ll T){vector<int>owner(V,-1),seen(V);int stamp=0,matched=0;
 function<bool(int)>dfs=[&](int u){for(int v=0;v<V;v++)if(d[u][v]<=T&&seen[v]!=stamp){seen[v]=stamp;if(owner[v]==-1||dfs(owner[v])){owner[v]=u;return true;}}return false;};
 for(int i=0;i<N;i++){++stamp;if(dfs(i)&&++matched>=K)return true;}return false;};
 if(!feasible(values.back())){cout<<-1<<'\n';return 0;}
 int lo=0,hi=(int)values.size()-1;while(lo<hi){int mid=(lo+hi)/2;if(feasible(values[mid]))hi=mid;else lo=mid+1;}cout<<values[lo]<<'\n';
}'''),
'852/E': ('''Assign a binary casino variable to every vertex. For a fixed start, each possible maximal journey ends at an original leaf other than the start (for n>1). Good final mood requires even parity on each start-to-terminal path. These equations are independent over GF(2): each terminal leaf's variable occurs in only its own equation, because a leaf cannot be internal on another path. If there are k leaves, the rank is k for a nonleaf start and k-1 for a leaf start. Hence sum k*2^(n-k+1)+(n-k)*2^(n-k) modulo 1000000007. For n=1 only the empty casino set works. O(n) time to read degrees and O(n) space.''', r'''#include <bits/stdc++.h>
using namespace std;using ll=long long;const ll MOD=1000000007;
ll power(ll a,int e){ll r=1;for(;e;e>>=1,a=a*a%MOD)if(e&1)r=r*a%MOD;return r;}
int main(){ios::sync_with_stdio(false);cin.tie(nullptr);int n;cin>>n;vector<int>d(n);
 for(int i=1,u,v;i<n;i++){cin>>u>>v;++d[u-1];++d[v-1];}
 if(n==1){cout<<1<<'\n';return 0;}int k=count(d.begin(),d.end(),1);
 cout<<(k*power(2,n-k+1)+(n-k)*power(2,n-k))%MOD<<'\n';
}''')}


def main():
    OUT.mkdir(exist_ok=True)
    for split in ('train', 'test'):
        with (OUT / f'{split}_answers.jsonl').open('w', encoding='utf-8') as sink:
            for line in (ROOT / f'{split}_problems.jsonl').open(encoding='utf-8'):
                row = json.loads(line)
                answer = ANSWERS.get(row['id'])
                record = {'id': row['id'], 'split': split, 'author': 'current chat assistant',
                          'status': 'authored' if answer else 'pending',
                          'explanation': answer[0] if answer else None,
                          'cpp_code': answer[1] if answer else None,
                          'validation': 'not yet validated',
                          'problem_sha256': hashlib.sha256(line.encode()).hexdigest()}
                sink.write(json.dumps(record, ensure_ascii=False) + '\n')
                if answer:
                    (OUT / (row['id'].replace('/', '_') + '.cpp')).write_text(answer[1])


if __name__ == '__main__':
    main()
