#include <nlohmann/json.hpp>
#include <chrono>
#include <fstream>
#include <iostream>
#include <atomic>
#include <cstdlib>
#include <new>
using Json=nlohmann::json;
std::atomic<size_t> calls{0},bytes{0};
void* operator new(size_t n){if(void*p=std::malloc(n?n:1)){++calls;bytes+=n;return p;}throw std::bad_alloc();}
void operator delete(void*p) noexcept{std::free(p);}
void operator delete(void*p,size_t) noexcept{std::free(p);}
const Json identity={{"name","freeflight"},{"version","diagnostic"}};
std::string oldResponse(Json value,bool modern){
 Json response={{"content",Json::array({{{"type","text"},{"text",value.dump()}}})},{"structuredContent",value.is_object()?value:Json{{"items",value}}},{"isError",false}};
 auto result=[&](Json value){if(modern){value["resultType"]="complete";value["_meta"]={{"io.modelcontextprotocol/serverInfo",identity}};}return Json{{"jsonrpc","2.0"},{"id",1},{"result",value}}.dump();};
 return result(response);
}
std::string movedResponse(Json value,bool modern){
 Json response=Json::object();Json content={{"type","text"},{"text",value.dump()}};
 response["content"]=Json::array();response["content"].push_back(std::move(content));
 if(value.is_object())response["structuredContent"]=std::move(value);else response["structuredContent"]["items"]=std::move(value);
 response["isError"]=false;
 if(modern){response["resultType"]="complete";response["_meta"]={{"io.modelcontextprotocol/serverInfo",identity}};}
 Json envelope={{"jsonrpc","2.0"},{"id",1}};envelope["result"]=std::move(response);return envelope.dump();
}
int main(int argc,char**argv){if(argc!=2)return 2;std::ifstream in(argv[1]);Json payload;in>>payload;
 for(auto p:std::vector<Json>{payload,Json::array(),Json::object(),nullptr,"x",42,{{"nested",payload}}})for(bool modern:{false,true})if(oldResponse(p,modern)!=movedResponse(p,modern))return 3;
 Json rows=Json::array();
 for(int i=-20;i<100;i++)for(int slot=0;slot<2;slot++){
 bool moved=(i%2==0)?slot==0:slot==1;Json input=payload; // equal input copy excluded from diagnostic
 auto c=calls.load(),b=bytes.load();auto start=std::chrono::steady_clock::now();
 auto output=moved?movedResponse(std::move(input),true):oldResponse(std::move(input),true);
 double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();auto nc=calls.load()-c,nb=bytes.load()-b;
 if(i>=0)rows.push_back({{"round",i},{"moved",moved},{"ms",ms},{"allocations",nc},{"allocatedBytes",nb},{"outputBytes",output.size()}});
 }
 std::cout<<Json{{"byteEqualityCases",14},{"samples",rows}}.dump()<<'\n';
}
