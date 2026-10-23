// SPDX-License-Identifier: Apache-2.0
#include <cstdint>
#include <iostream>
#include <thread>
#include <unistd.h>
struct WorkStamp {uint64_t instructions,cycles,cpuNs,beginNs,endNs;int32_t pid,status;};
extern "C" int ffwork_read(WorkStamp*);
extern "C" uint64_t ffwork_loop(uint64_t,uint64_t);
volatile uint64_t sink=3;
WorkStamp read(){WorkStamp s{};if(ffwork_read(&s)||s.status)throw 1;return s;}
void difference(WorkStamp a,WorkStamp b){if(a.pid!=b.pid||b.instructions<a.instructions||b.cycles<a.cycles||b.cpuNs<a.cpuNs||b.beginNs<a.endNs)throw 2;std::cout<<"{\"instructions\":"<<b.instructions-a.instructions<<",\"cycles\":"<<b.cycles-a.cycles<<",\"cpuNs\":"<<b.cpuNs-a.cpuNs<<",\"wallNs\":"<<b.beginNs-a.endNs<<"}";}
void run(const char* thread){
 for(int r=0;r<1000;r++){auto a=read();auto b=read();std::cout<<"{\"kind\":\"empty\",\"thread\":\""<<thread<<"\",\"delta\":";difference(a,b);std::cout<<"}\n";}
 for(int rep=0;rep<7;rep++)for(uint64_t n: {10000,50000,100000,500000})for(int gap: {0,1})for(int j=0;j<2;j++){
  int factor=(rep%2?2-j:1+j);if(gap)usleep(25000);
  auto a=read();sink=ffwork_loop(n*factor/2,3);auto b=read();usleep(3000);auto c=read();sink=ffwork_loop(n*factor/2,7);auto d=read();
  std::cout<<"{\"kind\":\"nested\",\"thread\":\""<<thread<<"\",\"repeat\":"<<rep<<",\"size\":"<<n<<",\"gap\":"<<gap<<",\"factor\":"<<factor<<",\"outer\":";difference(a,d);std::cout<<",\"inner\":";difference(b,c);std::cout<<",\"pre\":";difference(a,b);std::cout<<",\"post\":";difference(c,d);std::cout<<"}\n";
 }
}
int main(){run("main");std::thread worker([]{run("executor");});worker.join();}
