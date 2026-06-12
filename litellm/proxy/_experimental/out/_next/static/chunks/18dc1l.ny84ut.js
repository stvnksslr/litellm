(globalThis.TURBOPACK||(globalThis.TURBOPACK=[])).push(["object"==typeof document?document.currentScript:void 0,618566,(e,t,r)=>{t.exports=e.r(976562)},612256,869230,469637,266027,243652,e=>{"use strict";let t;var r=e.i(602869),i=e.i(175555),o=e.i(273911),a=e.i(540143),n=e.i(286491),s=e.i(915823),l=e.i(793803),u=e.i(619273),d=e.i(180166),c=class extends s.Subscribable{constructor(e,t){super(),this.options=t,this.#e=e,this.#t=null,this.#r=(0,l.pendingThenable)(),this.bindMethods(),this.setOptions(t)}#e;#i=void 0;#o=void 0;#a=void 0;#n;#s;#r;#t;#l;#u;#d;#c;#p;#h;#m=new Set;bindMethods(){this.refetch=this.refetch.bind(this)}onSubscribe(){1===this.listeners.size&&(this.#i.addObserver(this),p(this.#i,this.options)?this.#g():this.updateResult(),this.#f())}onUnsubscribe(){this.hasListeners()||this.destroy()}shouldFetchOnReconnect(){return h(this.#i,this.options,this.options.refetchOnReconnect)}shouldFetchOnWindowFocus(){return h(this.#i,this.options,this.options.refetchOnWindowFocus)}destroy(){this.listeners=new Set,this.#b(),this.#_(),this.#i.removeObserver(this)}setOptions(e){let t=this.options,r=this.#i;if(this.options=this.#e.defaultQueryOptions(e),void 0!==this.options.enabled&&"boolean"!=typeof this.options.enabled&&"function"!=typeof this.options.enabled&&"boolean"!=typeof(0,u.resolveQueryBoolean)(this.options.enabled,this.#i))throw Error("Expected enabled to be a boolean or a callback that returns a boolean");this.#y(),this.#i.setOptions(this.options),t._defaulted&&!(0,u.shallowEqualObjects)(this.options,t)&&this.#e.getQueryCache().notify({type:"observerOptionsUpdated",query:this.#i,observer:this});let i=this.hasListeners();i&&m(this.#i,r,this.options,t)&&this.#g(),this.updateResult(),i&&(this.#i!==r||(0,u.resolveQueryBoolean)(this.options.enabled,this.#i)!==(0,u.resolveQueryBoolean)(t.enabled,this.#i)||(0,u.resolveStaleTime)(this.options.staleTime,this.#i)!==(0,u.resolveStaleTime)(t.staleTime,this.#i))&&this.#v();let o=this.#x();i&&(this.#i!==r||(0,u.resolveQueryBoolean)(this.options.enabled,this.#i)!==(0,u.resolveQueryBoolean)(t.enabled,this.#i)||o!==this.#h)&&this.#C(o)}getOptimisticResult(e){var t,r;let i=this.#e.getQueryCache().build(this.#e,e),o=this.createResult(i,e);return t=this,r=o,(0,u.shallowEqualObjects)(t.getCurrentResult(),r)||(this.#a=o,this.#s=this.options,this.#n=this.#i.state),o}getCurrentResult(){return this.#a}trackResult(e,t){return new Proxy(e,{get:(e,r)=>(this.trackProp(r),t?.(r),"promise"===r&&(this.trackProp("data"),this.options.experimental_prefetchInRender||"pending"!==this.#r.status||this.#r.reject(Error("experimental_prefetchInRender feature flag is not enabled"))),Reflect.get(e,r))})}trackProp(e){this.#m.add(e)}getCurrentQuery(){return this.#i}refetch({...e}={}){return this.fetch({...e})}fetchOptimistic(e){let t=this.#e.defaultQueryOptions(e),r=this.#e.getQueryCache().build(this.#e,t);return r.fetch().then(()=>this.createResult(r,t))}fetch(e){return this.#g({...e,cancelRefetch:e.cancelRefetch??!0}).then(()=>(this.updateResult(),this.#a))}#g(e){this.#y();let t=this.#i.fetch(this.options,e);return e?.throwOnError||(t=t.catch(u.noop)),t}#v(){this.#b();let e=(0,u.resolveStaleTime)(this.options.staleTime,this.#i);if(o.environmentManager.isServer()||this.#a.isStale||!(0,u.isValidTimeout)(e))return;let t=(0,u.timeUntilStale)(this.#a.dataUpdatedAt,e);this.#c=d.timeoutManager.setTimeout(()=>{this.#a.isStale||this.updateResult()},t+1)}#x(){return("function"==typeof this.options.refetchInterval?this.options.refetchInterval(this.#i):this.options.refetchInterval)??!1}#C(e){this.#_(),this.#h=e,!o.environmentManager.isServer()&&!1!==(0,u.resolveQueryBoolean)(this.options.enabled,this.#i)&&(0,u.isValidTimeout)(this.#h)&&0!==this.#h&&(this.#p=d.timeoutManager.setInterval(()=>{(this.options.refetchIntervalInBackground||i.focusManager.isFocused())&&this.#g()},this.#h))}#f(){this.#v(),this.#C(this.#x())}#b(){void 0!==this.#c&&(d.timeoutManager.clearTimeout(this.#c),this.#c=void 0)}#_(){void 0!==this.#p&&(d.timeoutManager.clearInterval(this.#p),this.#p=void 0)}createResult(e,t){let r,i=this.#i,o=this.options,a=this.#a,s=this.#n,d=this.#s,c=e!==i?e.state:this.#o,{state:h}=e,f={...h},b=!1;if(t._optimisticResults){let r=this.hasListeners(),a=!r&&p(e,t),s=r&&m(e,i,t,o);(a||s)&&(f={...f,...(0,n.fetchState)(h.data,e.options)}),"isRestoring"===t._optimisticResults&&(f.fetchStatus="idle")}let{error:_,errorUpdatedAt:y,status:v}=f;r=f.data;let x=!1;if(void 0!==t.placeholderData&&void 0===r&&"pending"===v){let e;a?.isPlaceholderData&&t.placeholderData===d?.placeholderData?(e=a.data,x=!0):e="function"==typeof t.placeholderData?t.placeholderData(this.#d?.state.data,this.#d):t.placeholderData,void 0!==e&&(v="success",r=(0,u.replaceData)(a?.data,e,t),b=!0)}if(t.select&&void 0!==r&&!x)if(a&&r===s?.data&&t.select===this.#l)r=this.#u;else try{this.#l=t.select,r=t.select(r),r=(0,u.replaceData)(a?.data,r,t),this.#u=r,this.#t=null}catch(e){this.#t=e}this.#t&&(_=this.#t,r=this.#u,y=Date.now(),v="error");let C="fetching"===f.fetchStatus,w="pending"===v,R="error"===v,S=w&&C,k=void 0!==r,I={status:v,fetchStatus:f.fetchStatus,isPending:w,isSuccess:"success"===v,isError:R,isInitialLoading:S,isLoading:S,data:r,dataUpdatedAt:f.dataUpdatedAt,error:_,errorUpdatedAt:y,failureCount:f.fetchFailureCount,failureReason:f.fetchFailureReason,errorUpdateCount:f.errorUpdateCount,isFetched:e.isFetched(),isFetchedAfterMount:f.dataUpdateCount>c.dataUpdateCount||f.errorUpdateCount>c.errorUpdateCount,isFetching:C,isRefetching:C&&!w,isLoadingError:R&&!k,isPaused:"paused"===f.fetchStatus,isPlaceholderData:b,isRefetchError:R&&k,isStale:g(e,t),refetch:this.refetch,promise:this.#r,isEnabled:!1!==(0,u.resolveQueryBoolean)(t.enabled,e)};if(this.options.experimental_prefetchInRender){let t=void 0!==I.data,r="error"===I.status&&!t,o=e=>{r?e.reject(I.error):t&&e.resolve(I.data)},a=()=>{o(this.#r=I.promise=(0,l.pendingThenable)())},n=this.#r;switch(n.status){case"pending":e.queryHash===i.queryHash&&o(n);break;case"fulfilled":(r||I.data!==n.value)&&a();break;case"rejected":r&&I.error===n.reason||a()}}return I}updateResult(){let e=this.#a,t=this.createResult(this.#i,this.options);if(this.#n=this.#i.state,this.#s=this.options,void 0!==this.#n.data&&(this.#d=this.#i),(0,u.shallowEqualObjects)(t,e))return;this.#a=t;let r=()=>{if(!e)return!0;let{notifyOnChangeProps:t}=this.options,r="function"==typeof t?t():t;if("all"===r||!r&&!this.#m.size)return!0;let i=new Set(r??this.#m);return this.options.throwOnError&&i.add("error"),Object.keys(this.#a).some(t=>this.#a[t]!==e[t]&&i.has(t))};this.#w({listeners:r()})}#y(){let e=this.#e.getQueryCache().build(this.#e,this.options);if(e===this.#i)return;let t=this.#i;this.#i=e,this.#o=e.state,this.hasListeners()&&(t?.removeObserver(this),e.addObserver(this))}onQueryUpdate(){this.updateResult(),this.hasListeners()&&this.#f()}#w(e){a.notifyManager.batch(()=>{e.listeners&&this.listeners.forEach(e=>{e(this.#a)}),this.#e.getQueryCache().notify({query:this.#i,type:"observerResultsUpdated"})})}};function p(e,t){return!1!==(0,u.resolveQueryBoolean)(t.enabled,e)&&void 0===e.state.data&&("error"!==e.state.status||!1!==(0,u.resolveQueryBoolean)(t.retryOnMount,e))||void 0!==e.state.data&&h(e,t,t.refetchOnMount)}function h(e,t,r){if(!1!==(0,u.resolveQueryBoolean)(t.enabled,e)&&"static"!==(0,u.resolveStaleTime)(t.staleTime,e)){let i="function"==typeof r?r(e):r;return"always"===i||!1!==i&&g(e,t)}return!1}function m(e,t,r,i){return(e!==t||!1===(0,u.resolveQueryBoolean)(i.enabled,e))&&(!r.suspense||"error"!==e.state.status)&&g(e,r)}function g(e,t){return!1!==(0,u.resolveQueryBoolean)(t.enabled,e)&&e.isStaleByTime((0,u.resolveStaleTime)(t.staleTime,e))}e.s(["QueryObserver",0,c],869230),e.i(247167);var f=e.i(271645),b=e.i(912598);e.i(843476);var _=f.createContext((t=!1,{clearReset:()=>{t=!1},reset:()=>{t=!0},isReset:()=>t})),y=f.createContext(!1);y.Provider;var v=(e,t,r)=>t.fetchOptimistic(e).catch(()=>{r.clearReset()});function x(e,t,r){let i,n=f.useContext(y),s=f.useContext(_),l=(0,b.useQueryClient)(r),d=l.defaultQueryOptions(e);l.getDefaultOptions().queries?._experimental_beforeQuery?.(d);let c=l.getQueryCache().get(d.queryHash);if(d._optimisticResults=n?"isRestoring":"optimistic",d.suspense){let e=e=>"static"===e?e:Math.max(e??1e3,1e3),t=d.staleTime;d.staleTime="function"==typeof t?(...r)=>e(t(...r)):e(t),"number"==typeof d.gcTime&&(d.gcTime=Math.max(d.gcTime,1e3))}i=c?.state.error&&"function"==typeof d.throwOnError?(0,u.shouldThrowError)(d.throwOnError,[c.state.error,c]):d.throwOnError,(d.suspense||d.experimental_prefetchInRender||i)&&!s.isReset()&&(d.retryOnMount=!1),f.useEffect(()=>{s.clearReset()},[s]);let p=!l.getQueryCache().get(d.queryHash),[h]=f.useState(()=>new t(l,d)),m=h.getOptimisticResult(d),g=!n&&!1!==e.subscribed;if(f.useSyncExternalStore(f.useCallback(e=>{let t=g?h.subscribe(a.notifyManager.batchCalls(e)):u.noop;return h.updateResult(),t},[h,g]),()=>h.getCurrentResult(),()=>h.getCurrentResult()),f.useEffect(()=>{h.setOptions(d)},[d,h]),d?.suspense&&m.isPending)throw v(d,h,s);if((({result:e,errorResetBoundary:t,throwOnError:r,query:i,suspense:o})=>e.isError&&!t.isReset()&&!e.isFetching&&i&&(o&&void 0===e.data||(0,u.shouldThrowError)(r,[e.error,i])))({result:m,errorResetBoundary:s,throwOnError:d.throwOnError,query:c,suspense:d.suspense}))throw m.error;if(l.getDefaultOptions().queries?._experimental_afterQuery?.(d,m),d.experimental_prefetchInRender&&!o.environmentManager.isServer()&&m.isLoading&&m.isFetching&&!n){let e=p?v(d,h,s):c?.promise;e?.catch(u.noop).finally(()=>{h.updateResult()})}return d.notifyOnChangeProps?m:h.trackResult(m)}function C(e,t){return x(e,c,t)}function w(e){let t=[e];return{all:t,lists:()=>[...t,"list"],list:e=>[...t,"list",{params:e}],details:()=>[...t,"detail"],detail:e=>[...t,"detail",e]}}e.s(["useBaseQuery",0,x],469637),e.s(["useQuery",0,C],266027),e.s(["createQueryKeys",0,w],243652);let R=w("uiConfig");e.s(["useUIConfig",0,()=>C({queryKey:R.list({}),queryFn:async()=>await (0,r.getUiConfig)(),staleTime:864e5,gcTime:864e5})],612256)},321836,e=>{"use strict";let t="litellm_return_url",r="redirect_to";function i(){return window.location.href}function o(){if("u"<typeof document)return null;let e=document.cookie.match(RegExp(`(^| )${t}=([^;]+)`));if(e)try{return decodeURIComponent(e[2])}catch{return e[2]}return null}function a(){try{"u">typeof document&&(document.cookie=`${t}=; path=/; max-age=0`)}catch(e){console.error("Failed to clear return URL cookie:",e)}}function n(){return new URLSearchParams(window.location.search).get(r)}function s(){let e=window.location.hostname;return"localhost"===e||"127.0.0.1"===e||"::1"===e||e.startsWith("127.")||e.endsWith(".local")}function l(e){if(!e)return!1;if(e.startsWith("/")&&!e.startsWith("//"))return!0;try{let t=new URL(e),r=window.location.hostname;if(t.hostname!==r)return!1;if(s())return!0;return t.origin===window.location.origin}catch{return!1}}e.s(["buildLoginUrlWithReturn",0,function(e,t){let o=t||i();if(!o||o.includes("/login"))return e;let a=e.includes("?")?"&":"?";return`${e}${a}${r}=${encodeURIComponent(o)}`},"clearStoredReturnUrl",0,a,"consumeReturnUrl",0,function(){let e=n();if(e){if(l(e))return a(),e;s()&&console.warn("[returnUrlUtils] Invalid return URL in params rejected:",e)}let t=o();if(t){if(l(t))return a(),t;s()&&console.warn("[returnUrlUtils] Invalid return URL in cookie rejected:",t)}return null},"getReturnUrl",0,function(){let e=n();if(e)return e;let t=o();return t||null},"isValidReturnUrl",0,l,"normalizeUrlForCompare",0,function(e){try{let t=new URL(e,window.location.origin),r=t.pathname;r.length>1&&r.endsWith("/")&&(r=r.slice(0,-1));let i=new URLSearchParams(t.search),o=new URLSearchParams;Array.from(i.entries()).sort(([e],[t])=>e.localeCompare(t)).forEach(([e,t])=>{o.append(e,t)});let a=o.toString(),n=t.hash||"";return`${t.origin}${r}${a?`?${a}`:""}${n}`}catch{return e}},"storeReturnUrl",0,function(){let e=i();e&&function(e,t,r=300){if("u"<typeof document)return;let i="https:"===window.location.protocol;document.cookie=`${e}=${encodeURIComponent(t)}; path=/; max-age=${r}; SameSite=Lax${i?"; Secure":""}`}(t,e,300)}])},95779,e=>{"use strict";var t=e.i(480731);let r=[t.BaseColors.Blue,t.BaseColors.Cyan,t.BaseColors.Sky,t.BaseColors.Indigo,t.BaseColors.Violet,t.BaseColors.Purple,t.BaseColors.Fuchsia,t.BaseColors.Slate,t.BaseColors.Gray,t.BaseColors.Zinc,t.BaseColors.Neutral,t.BaseColors.Stone,t.BaseColors.Red,t.BaseColors.Orange,t.BaseColors.Amber,t.BaseColors.Yellow,t.BaseColors.Lime,t.BaseColors.Green,t.BaseColors.Emerald,t.BaseColors.Teal,t.BaseColors.Pink,t.BaseColors.Rose];e.s(["colorPalette",0,{canvasBackground:50,lightBackground:100,background:500,darkBackground:600,darkestBackground:800,lightBorder:200,border:500,darkBorder:700,lightRing:200,ring:300,iconRing:500,lightText:400,text:500,iconText:600,darkText:700,darkestText:900,icon:500},"themeColorRange",0,r])},135214,e=>{"use strict";var t=e.i(602869),r=e.i(268004),i=e.i(161281),o=e.i(321836),a=e.i(618566),n=e.i(271645),s=e.i(708347),l=e.i(612256);e.s(["default",0,()=>{let e=(0,a.useRouter)(),{data:u,isLoading:d}=(0,l.useUIConfig)(),c="u">typeof document?(0,r.getCookie)("token"):null,p=(0,n.useMemo)(()=>(0,i.decodeToken)(c),[c]),h=(0,n.useMemo)(()=>(0,i.checkTokenValidity)(c),[c])&&!u?.admin_ui_disabled,m=(0,n.useCallback)(()=>{(0,o.storeReturnUrl)();let r=`${(0,t.getProxyBaseUrl)()}/ui/login`,i=(0,o.buildLoginUrlWithReturn)(r);e.replace(i)},[e]);return(0,n.useEffect)(()=>{!d&&(h||(c&&(0,r.clearTokenCookies)(),m()))},[d,h,c,m]),{isLoading:d,isAuthorized:h,token:h?c:null,accessToken:p?.key??null,userId:p?.user_id??null,userEmail:p?.user_email??null,userRole:(0,s.formatUserRole)(p?.user_role),premiumUser:p?.premium_user??null,disabledPersonalKeyCreation:p?.disabled_non_admin_personal_key_creation??null,showSSOBanner:p?.login_method==="username_password"}}])},475254,e=>{"use strict";var t=e.i(271645);let r=e=>{let t=e.replace(/^([A-Z])|[\s-_]+(\w)/g,(e,t,r)=>r?r.toUpperCase():t.toLowerCase());return t.charAt(0).toUpperCase()+t.slice(1)},i=(...e)=>e.filter((e,t,r)=>!!e&&""!==e.trim()&&r.indexOf(e)===t).join(" ").trim();var o={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:2,strokeLinecap:"round",strokeLinejoin:"round"};let a=(0,t.forwardRef)(({color:e="currentColor",size:r=24,strokeWidth:a=2,absoluteStrokeWidth:n,className:s="",children:l,iconNode:u,...d},c)=>(0,t.createElement)("svg",{ref:c,...o,width:r,height:r,stroke:e,strokeWidth:n?24*Number(a)/Number(r):a,className:i("lucide",s),...!l&&!(e=>{for(let t in e)if(t.startsWith("aria-")||"role"===t||"title"===t)return!0})(d)&&{"aria-hidden":"true"},...d},[...u.map(([e,r])=>(0,t.createElement)(e,r)),...Array.isArray(l)?l:[l]]));e.s(["default",0,(e,o)=>{let n=(0,t.forwardRef)(({className:n,...s},l)=>(0,t.createElement)(a,{ref:l,iconNode:o,className:i(`lucide-${r(e).replace(/([a-z0-9])([A-Z])/g,"$1-$2").toLowerCase()}`,`lucide-${e}`,n),...s}));return n.displayName=r(e),n}],475254)},62478,e=>{"use strict";var t=e.i(602869);let r=async e=>{if(!e)return null;try{return await (0,t.getProxyUISettings)(e)}catch(e){return console.error("Error fetching proxy settings:",e),null}};e.s(["fetchProxySettings",0,r])},599724,936325,e=>{"use strict";var t=e.i(95779),r=e.i(444755),i=e.i(673706),o=e.i(271645);let a=o.default.forwardRef((e,a)=>{let{color:n,className:s,children:l}=e;return o.default.createElement("p",{ref:a,className:(0,r.tremorTwMerge)("text-tremor-default",n?(0,i.getColorClassNames)(n,t.colorPalette.text).textColor:(0,r.tremorTwMerge)("text-tremor-content","dark:text-dark-tremor-content"),s)},l)});a.displayName="Text",e.s(["default",0,a],936325),e.s(["Text",0,a],599724)},56456,e=>{"use strict";var t=e.i(739295);e.s(["LoadingOutlined",()=>t.default])},818581,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"useMergedRef",{enumerable:!0,get:function(){return o}});let i=e.r(271645);function o(e,t){let r=(0,i.useRef)(null),o=(0,i.useRef)(null);return(0,i.useCallback)(i=>{if(null===i){let e=r.current;e&&(r.current=null,e());let t=o.current;t&&(o.current=null,t())}else e&&(r.current=a(e,i)),t&&(o.current=a(t,i))},[e,t])}function a(e,t){if("function"!=typeof e)return e.current=t,()=>{e.current=null};{let r=e(t);return"function"==typeof r?r:()=>e(null)}}("function"==typeof r.default||"object"==typeof r.default&&null!==r.default)&&void 0===r.default.__esModule&&(Object.defineProperty(r.default,"__esModule",{value:!0}),Object.assign(r.default,r),t.exports=r.default)},602073,312361,e=>{"use strict";e.i(247167);var t=e.i(931067),r=e.i(271645);let i={icon:{tag:"svg",attrs:{viewBox:"0 0 1024 1024",focusable:"false"},children:[{tag:"path",attrs:{d:"M512 64L128 192v384c0 212.1 171.9 384 384 384s384-171.9 384-384V192L512 64zm312 512c0 172.3-139.7 312-312 312S200 748.3 200 576V246l312-110 312 110v330z"}},{tag:"path",attrs:{d:"M378.4 475.1a35.91 35.91 0 00-50.9 0 35.91 35.91 0 000 50.9l129.4 129.4 2.1 2.1a33.98 33.98 0 0048.1 0L730.6 434a33.98 33.98 0 000-48.1l-2.8-2.8a33.98 33.98 0 00-48.1 0L483 579.7 378.4 475.1z"}}]},name:"safety",theme:"outlined"};var o=e.i(9583),a=r.forwardRef(function(e,a){return r.createElement(o.default,(0,t.default)({},e,{ref:a,icon:i}))});e.s(["SafetyOutlined",0,a],602073);var n=e.i(343794),s=e.i(242064),l=e.i(517455);e.i(296059);var u=e.i(915654),d=e.i(183293),c=e.i(246422),p=e.i(838378);let h=(0,c.genStyleHooks)("Divider",e=>{let t=(0,p.mergeToken)(e,{dividerHorizontalWithTextGutterMargin:e.margin,sizePaddingEdgeHorizontal:0});return[(e=>{let{componentCls:t,sizePaddingEdgeHorizontal:r,colorSplit:i,lineWidth:o,textPaddingInline:a,orientationMargin:n,verticalMarginInline:s}=e;return{[t]:Object.assign(Object.assign({},(0,d.resetComponent)(e)),{borderBlockStart:`${(0,u.unit)(o)} solid ${i}`,"&-vertical":{position:"relative",top:"-0.06em",display:"inline-block",height:"0.9em",marginInline:s,marginBlock:0,verticalAlign:"middle",borderTop:0,borderInlineStart:`${(0,u.unit)(o)} solid ${i}`},"&-horizontal":{display:"flex",clear:"both",width:"100%",minWidth:"100%",margin:`${(0,u.unit)(e.marginLG)} 0`},[`&-horizontal${t}-with-text`]:{display:"flex",alignItems:"center",margin:`${(0,u.unit)(e.dividerHorizontalWithTextGutterMargin)} 0`,color:e.colorTextHeading,fontWeight:500,fontSize:e.fontSizeLG,whiteSpace:"nowrap",textAlign:"center",borderBlockStart:`0 ${i}`,"&::before, &::after":{position:"relative",width:"50%",borderBlockStart:`${(0,u.unit)(o)} solid transparent`,borderBlockStartColor:"inherit",borderBlockEnd:0,transform:"translateY(50%)",content:"''"}},[`&-horizontal${t}-with-text-start`]:{"&::before":{width:`calc(${n} * 100%)`},"&::after":{width:`calc(100% - ${n} * 100%)`}},[`&-horizontal${t}-with-text-end`]:{"&::before":{width:`calc(100% - ${n} * 100%)`},"&::after":{width:`calc(${n} * 100%)`}},[`${t}-inner-text`]:{display:"inline-block",paddingBlock:0,paddingInline:a},"&-dashed":{background:"none",borderColor:i,borderStyle:"dashed",borderWidth:`${(0,u.unit)(o)} 0 0`},[`&-horizontal${t}-with-text${t}-dashed`]:{"&::before, &::after":{borderStyle:"dashed none none"}},[`&-vertical${t}-dashed`]:{borderInlineStartWidth:o,borderInlineEnd:0,borderBlockStart:0,borderBlockEnd:0},"&-dotted":{background:"none",borderColor:i,borderStyle:"dotted",borderWidth:`${(0,u.unit)(o)} 0 0`},[`&-horizontal${t}-with-text${t}-dotted`]:{"&::before, &::after":{borderStyle:"dotted none none"}},[`&-vertical${t}-dotted`]:{borderInlineStartWidth:o,borderInlineEnd:0,borderBlockStart:0,borderBlockEnd:0},[`&-plain${t}-with-text`]:{color:e.colorText,fontWeight:"normal",fontSize:e.fontSize},[`&-horizontal${t}-with-text-start${t}-no-default-orientation-margin-start`]:{"&::before":{width:0},"&::after":{width:"100%"},[`${t}-inner-text`]:{paddingInlineStart:r}},[`&-horizontal${t}-with-text-end${t}-no-default-orientation-margin-end`]:{"&::before":{width:"100%"},"&::after":{width:0},[`${t}-inner-text`]:{paddingInlineEnd:r}}})}})(t),(e=>{let{componentCls:t}=e;return{[t]:{"&-horizontal":{[`&${t}`]:{"&-sm":{marginBlock:e.marginXS},"&-md":{marginBlock:e.margin}}}}}})(t)]},e=>({textPaddingInline:"1em",orientationMargin:.05,verticalMarginInline:e.marginXS}),{unitless:{orientationMargin:!0}});var m=function(e,t){var r={};for(var i in e)Object.prototype.hasOwnProperty.call(e,i)&&0>t.indexOf(i)&&(r[i]=e[i]);if(null!=e&&"function"==typeof Object.getOwnPropertySymbols)for(var o=0,i=Object.getOwnPropertySymbols(e);o<i.length;o++)0>t.indexOf(i[o])&&Object.prototype.propertyIsEnumerable.call(e,i[o])&&(r[i[o]]=e[i[o]]);return r};let g={small:"sm",middle:"md"};e.s(["Divider",0,e=>{let{getPrefixCls:t,direction:i,className:o,style:a}=(0,s.useComponentConfig)("divider"),{prefixCls:u,type:d="horizontal",orientation:c="center",orientationMargin:p,className:f,rootClassName:b,children:_,dashed:y,variant:v="solid",plain:x,style:C,size:w}=e,R=m(e,["prefixCls","type","orientation","orientationMargin","className","rootClassName","children","dashed","variant","plain","style","size"]),S=t("divider",u),[k,I,T]=h(S),E=g[(0,l.default)(w)],O=!!_,$=r.useMemo(()=>"left"===c?"rtl"===i?"end":"start":"right"===c?"rtl"===i?"start":"end":c,[i,c]),B="start"===$&&null!=p,P="end"===$&&null!=p,N=(0,n.default)(S,o,I,T,`${S}-${d}`,{[`${S}-with-text`]:O,[`${S}-with-text-${$}`]:O,[`${S}-dashed`]:!!y,[`${S}-${v}`]:"solid"!==v,[`${S}-plain`]:!!x,[`${S}-rtl`]:"rtl"===i,[`${S}-no-default-orientation-margin-start`]:B,[`${S}-no-default-orientation-margin-end`]:P,[`${S}-${E}`]:!!E},f,b),M=r.useMemo(()=>"number"==typeof p?p:/^\d+$/.test(p)?Number(p):p,[p]);return k(r.createElement("div",Object.assign({className:N,style:Object.assign(Object.assign({},a),C)},R,{role:"separator"}),_&&"vertical"!==d&&r.createElement("span",{className:`${S}-inner-text`,style:{marginInlineStart:B?M:void 0,marginInlineEnd:P?M:void 0}},_)))}],312361)},994388,e=>{"use strict";var t=e.i(290571),r=e.i(829087),i=e.i(271645);let o=["preEnter","entering","entered","preExit","exiting","exited","unmounted"],a=e=>({_s:e,status:o[e],isEnter:e<3,isMounted:6!==e,isResolved:2===e||e>4}),n=e=>e?6:5,s=(e,t,r,i,o)=>{clearTimeout(i.current);let n=a(e);t(n),r.current=n,o&&o({current:n})};var l=e.i(480731),u=e.i(444755),d=e.i(673706);let c=e=>{var r=(0,t.__rest)(e,[]);return i.default.createElement("svg",Object.assign({},r,{xmlns:"http://www.w3.org/2000/svg",viewBox:"0 0 24 24",fill:"currentColor"}),i.default.createElement("path",{fill:"none",d:"M0 0h24v24H0z"}),i.default.createElement("path",{d:"M18.364 5.636L16.95 7.05A7 7 0 1 0 19 12h2a9 9 0 1 1-2.636-6.364z"}))};var p=e.i(95779);let h={xs:{height:"h-4",width:"w-4"},sm:{height:"h-5",width:"w-5"},md:{height:"h-5",width:"w-5"},lg:{height:"h-6",width:"w-6"},xl:{height:"h-6",width:"w-6"}},m=(e,t)=>{switch(e){case"primary":return{textColor:t?(0,d.getColorClassNames)("white").textColor:"text-tremor-brand-inverted dark:text-dark-tremor-brand-inverted",hoverTextColor:t?(0,d.getColorClassNames)("white").textColor:"text-tremor-brand-inverted dark:text-dark-tremor-brand-inverted",bgColor:t?(0,d.getColorClassNames)(t,p.colorPalette.background).bgColor:"bg-tremor-brand dark:bg-dark-tremor-brand",hoverBgColor:t?(0,d.getColorClassNames)(t,p.colorPalette.darkBackground).hoverBgColor:"hover:bg-tremor-brand-emphasis dark:hover:bg-dark-tremor-brand-emphasis",borderColor:t?(0,d.getColorClassNames)(t,p.colorPalette.border).borderColor:"border-tremor-brand dark:border-dark-tremor-brand",hoverBorderColor:t?(0,d.getColorClassNames)(t,p.colorPalette.darkBorder).hoverBorderColor:"hover:border-tremor-brand-emphasis dark:hover:border-dark-tremor-brand-emphasis"};case"secondary":return{textColor:t?(0,d.getColorClassNames)(t,p.colorPalette.text).textColor:"text-tremor-brand dark:text-dark-tremor-brand",hoverTextColor:t?(0,d.getColorClassNames)(t,p.colorPalette.text).textColor:"hover:text-tremor-brand-emphasis dark:hover:text-dark-tremor-brand-emphasis",bgColor:(0,d.getColorClassNames)("transparent").bgColor,hoverBgColor:t?(0,u.tremorTwMerge)((0,d.getColorClassNames)(t,p.colorPalette.background).hoverBgColor,"hover:bg-opacity-20 dark:hover:bg-opacity-20"):"hover:bg-tremor-brand-faint dark:hover:bg-dark-tremor-brand-faint",borderColor:t?(0,d.getColorClassNames)(t,p.colorPalette.border).borderColor:"border-tremor-brand dark:border-dark-tremor-brand"};case"light":return{textColor:t?(0,d.getColorClassNames)(t,p.colorPalette.text).textColor:"text-tremor-brand dark:text-dark-tremor-brand",hoverTextColor:t?(0,d.getColorClassNames)(t,p.colorPalette.darkText).hoverTextColor:"hover:text-tremor-brand-emphasis dark:hover:text-dark-tremor-brand-emphasis",bgColor:(0,d.getColorClassNames)("transparent").bgColor,borderColor:"",hoverBorderColor:""}}},g=(0,d.makeClassName)("Button"),f=({loading:e,iconSize:t,iconPosition:r,Icon:o,needMargin:a,transitionStatus:n})=>{let s=a?r===l.HorizontalPositions.Left?(0,u.tremorTwMerge)("-ml-1","mr-1.5"):(0,u.tremorTwMerge)("-mr-1","ml-1.5"):"",d=(0,u.tremorTwMerge)("w-0 h-0"),p={default:d,entering:d,entered:t,exiting:t,exited:d};return e?i.default.createElement(c,{className:(0,u.tremorTwMerge)(g("icon"),"animate-spin shrink-0",s,p.default,p[n]),style:{transition:"width 150ms"}}):i.default.createElement(o,{className:(0,u.tremorTwMerge)(g("icon"),"shrink-0",t,s)})},b=i.default.forwardRef((e,o)=>{let{icon:c,iconPosition:p=l.HorizontalPositions.Left,size:b=l.Sizes.SM,color:_,variant:y="primary",disabled:v,loading:x=!1,loadingText:C,children:w,tooltip:R,className:S}=e,k=(0,t.__rest)(e,["icon","iconPosition","size","color","variant","disabled","loading","loadingText","children","tooltip","className"]),I=x||v,T=void 0!==c||x,E=x&&C,O=!(!w&&!E),$=(0,u.tremorTwMerge)(h[b].height,h[b].width),B="light"!==y?(0,u.tremorTwMerge)("rounded-tremor-default border","shadow-tremor-input","dark:shadow-dark-tremor-input"):"",P=m(y,_),N=("light"!==y?{xs:{paddingX:"px-2.5",paddingY:"py-1.5",fontSize:"text-xs"},sm:{paddingX:"px-4",paddingY:"py-2",fontSize:"text-sm"},md:{paddingX:"px-4",paddingY:"py-2",fontSize:"text-md"},lg:{paddingX:"px-4",paddingY:"py-2.5",fontSize:"text-lg"},xl:{paddingX:"px-4",paddingY:"py-3",fontSize:"text-xl"}}:{xs:{paddingX:"",paddingY:"",fontSize:"text-xs"},sm:{paddingX:"",paddingY:"",fontSize:"text-sm"},md:{paddingX:"",paddingY:"",fontSize:"text-md"},lg:{paddingX:"",paddingY:"",fontSize:"text-lg"},xl:{paddingX:"",paddingY:"",fontSize:"text-xl"}})[b],{tooltipProps:M,getReferenceProps:Q}=(0,r.useTooltip)(300),[j,z]=(({enter:e=!0,exit:t=!0,preEnter:r,preExit:o,timeout:l,initialEntered:u,mountOnEnter:d,unmountOnExit:c,onStateChange:p}={})=>{let[h,m]=(0,i.useState)(()=>a(u?2:n(d))),g=(0,i.useRef)(h),f=(0,i.useRef)(0),[b,_]="object"==typeof l?[l.enter,l.exit]:[l,l],y=(0,i.useCallback)(()=>{let e=((e,t)=>{switch(e){case 1:case 0:return 2;case 4:case 3:return n(t)}})(g.current._s,c);e&&s(e,m,g,f,p)},[p,c]);return[h,(0,i.useCallback)(i=>{let a=e=>{switch(s(e,m,g,f,p),e){case 1:b>=0&&(f.current=((...e)=>setTimeout(...e))(y,b));break;case 4:_>=0&&(f.current=((...e)=>setTimeout(...e))(y,_));break;case 0:case 3:f.current=((...e)=>setTimeout(...e))(()=>{isNaN(document.body.offsetTop)||a(e+1)},0)}},l=g.current.isEnter;"boolean"!=typeof i&&(i=!l),i?l||a(e?+!r:2):l&&a(t?o?3:4:n(c))},[y,p,e,t,r,o,b,_,c]),y]})({timeout:50});return(0,i.useEffect)(()=>{z(x)},[x]),i.default.createElement("button",Object.assign({ref:(0,d.mergeRefs)([o,M.refs.setReference]),className:(0,u.tremorTwMerge)(g("root"),"shrink-0 inline-flex justify-center items-center group font-medium outline-none",B,N.paddingX,N.paddingY,N.fontSize,P.textColor,P.bgColor,P.borderColor,P.hoverBorderColor,I?"opacity-50 cursor-not-allowed":(0,u.tremorTwMerge)(m(y,_).hoverTextColor,m(y,_).hoverBgColor,m(y,_).hoverBorderColor),S),disabled:I},Q,k),i.default.createElement(r.default,Object.assign({text:R},M)),T&&p!==l.HorizontalPositions.Right?i.default.createElement(f,{loading:x,iconSize:$,iconPosition:p,Icon:c,transitionStatus:j.status,needMargin:O}):null,E||w?i.default.createElement("span",{className:(0,u.tremorTwMerge)(g("text"),"text-tremor-default whitespace-nowrap")},E?C:w):null,T&&p===l.HorizontalPositions.Right?i.default.createElement(f,{loading:x,iconSize:$,iconPosition:p,Icon:c,transitionStatus:j.status,needMargin:O}):null)});b.displayName="Button",e.s(["Button",0,b],994388)},304967,e=>{"use strict";var t=e.i(290571),r=e.i(271645),i=e.i(480731),o=e.i(95779),a=e.i(444755),n=e.i(673706);let s=(0,n.makeClassName)("Card"),l=r.default.forwardRef((e,l)=>{let{decoration:u="",decorationColor:d,children:c,className:p}=e,h=(0,t.__rest)(e,["decoration","decorationColor","children","className"]);return r.default.createElement("div",Object.assign({ref:l,className:(0,a.tremorTwMerge)(s("root"),"relative w-full text-left ring-1 rounded-tremor-default p-6","bg-tremor-background ring-tremor-ring shadow-tremor-card","dark:bg-dark-tremor-background dark:ring-dark-tremor-ring dark:shadow-dark-tremor-card",d?(0,n.getColorClassNames)(d,o.colorPalette.border).borderColor:"border-tremor-brand dark:border-dark-tremor-brand",(e=>{if(!e)return"";switch(e){case i.HorizontalPositions.Left:return"border-l-4";case i.VerticalPositions.Top:return"border-t-4";case i.HorizontalPositions.Right:return"border-r-4";case i.VerticalPositions.Bottom:return"border-b-4";default:return""}})(u),p)},h),c)});l.displayName="Card",e.s(["Card",0,l],304967)},629569,e=>{"use strict";var t=e.i(290571),r=e.i(95779),i=e.i(444755),o=e.i(673706),a=e.i(271645);let n=a.default.forwardRef((e,n)=>{let{color:s,children:l,className:u}=e,d=(0,t.__rest)(e,["color","children","className"]);return a.default.createElement("p",Object.assign({ref:n,className:(0,i.tremorTwMerge)("font-medium text-tremor-title",s?(0,o.getColorClassNames)(s,r.colorPalette.darkText).textColor:"text-tremor-content-strong dark:text-dark-tremor-content-strong",u)},d),l)});n.displayName="Title",e.s(["Title",0,n],629569)},653496,e=>{"use strict";var t=e.i(721369);e.s(["Tabs",()=>t.default])},190272,785913,e=>{"use strict";var t,r,i=((t={}).AUDIO_SPEECH="audio_speech",t.AUDIO_TRANSCRIPTION="audio_transcription",t.IMAGE_GENERATION="image_generation",t.VIDEO_GENERATION="video_generation",t.CHAT="chat",t.RESPONSES="responses",t.IMAGE_EDITS="image_edits",t.ANTHROPIC_MESSAGES="anthropic_messages",t.EMBEDDING="embedding",t),o=((r={}).IMAGE="image",r.VIDEO="video",r.CHAT="chat",r.RESPONSES="responses",r.IMAGE_EDITS="image_edits",r.ANTHROPIC_MESSAGES="anthropic_messages",r.EMBEDDINGS="embeddings",r.SPEECH="speech",r.TRANSCRIPTION="transcription",r.A2A_AGENTS="a2a_agents",r.MCP="mcp",r.REALTIME="realtime",r.INTERACTIONS="interactions",r);let a={image_generation:"image",video_generation:"video",chat:"chat",responses:"responses",image_edits:"image_edits",anthropic_messages:"anthropic_messages",audio_speech:"speech",audio_transcription:"transcription",embedding:"embeddings"};e.s(["EndpointType",()=>o,"getEndpointType",0,e=>{if(console.log("getEndpointType:",e),Object.values(i).includes(e)){let t=a[e];return console.log("endpointType:",t),t}return"chat"}],785913),e.s(["generateCodeSnippet",0,e=>{let t,{apiKeySource:r,accessToken:i,apiKey:a,inputMessage:n,chatHistory:s,selectedTags:l,selectedVectorStores:u,selectedGuardrails:d,selectedPolicies:c,selectedMCPServers:p,mcpServers:h,mcpServerToolRestrictions:m,selectedVoice:g,endpointType:f,selectedModel:b,selectedSdk:_,proxySettings:y}=e,v="session"===r?i:a,x=window.location.origin,C=y?.LITELLM_UI_API_DOC_BASE_URL;C&&C.trim()?x=C:y?.PROXY_BASE_URL&&(x=y.PROXY_BASE_URL);let w=n||"Your prompt here",R=w.replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/\n/g,"\\n"),S=s.filter(e=>!e.isImage).map(({role:e,content:t})=>({role:e,content:t})),k={};l.length>0&&(k.tags=l),u.length>0&&(k.vector_stores=u),d.length>0&&(k.guardrails=d),c.length>0&&(k.policies=c);let I=b||"your-model-name",T="azure"===_?`import openai

client = openai.AzureOpenAI(
	api_key="${v||"YOUR_LITELLM_API_KEY"}",
	azure_endpoint="${x}",
	api_version="2024-02-01"
)`:`import openai

client = openai.OpenAI(
	api_key="${v||"YOUR_LITELLM_API_KEY"}",
	base_url="${x}"
)`;switch(f){case o.CHAT:{let e=Object.keys(k).length>0,r="";if(e){let e=JSON.stringify({metadata:k},null,2).split("\n").map(e=>" ".repeat(4)+e).join("\n").trim();r=`,
    extra_body=${e}`}let i=S.length>0?S:[{role:"user",content:w}];t=`
import base64

# Helper function to encode images to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Example with text only
response = client.chat.completions.create(
    model="${I}",
    messages=${JSON.stringify(i,null,4)}${r}
)

print(response)

# Example with image or PDF (uncomment and provide file path to use)
# base64_file = encode_image("path/to/your/file.jpg")  # or .pdf
# response_with_file = client.chat.completions.create(
#     model="${I}",
#     messages=[
#         {
#             "role": "user",
#             "content": [
#                 {
#                     "type": "text",
#                     "text": "${R}"
#                 },
#                 {
#                     "type": "image_url",
#                     "image_url": {
#                         "url": f"data:image/jpeg;base64,{base64_file}"  # or data:application/pdf;base64,{base64_file}
#                     }
#                 }
#             ]
#         }
#     ]${r}
# )
# print(response_with_file)
`;break}case o.RESPONSES:{let e=Object.keys(k).length>0,r="";if(e){let e=JSON.stringify({metadata:k},null,2).split("\n").map(e=>" ".repeat(4)+e).join("\n").trim();r=`,
    extra_body=${e}`}let i=S.length>0?S:[{role:"user",content:w}];t=`
import base64

# Helper function to encode images to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Example with text only
response = client.responses.create(
    model="${I}",
    input=${JSON.stringify(i,null,4)}${r}
)

print(response.output_text)

# Example with image or PDF (uncomment and provide file path to use)
# base64_file = encode_image("path/to/your/file.jpg")  # or .pdf
# response_with_file = client.responses.create(
#     model="${I}",
#     input=[
#         {
#             "role": "user",
#             "content": [
#                 {"type": "input_text", "text": "${R}"},
#                 {
#                     "type": "input_image",
#                     "image_url": f"data:image/jpeg;base64,{base64_file}",  # or data:application/pdf;base64,{base64_file}
#                 },
#             ],
#         }
#     ]${r}
# )
# print(response_with_file.output_text)
`;break}case o.IMAGE:t="azure"===_?`
# NOTE: The Azure SDK does not have a direct equivalent to the multi-modal 'responses.create' method shown for OpenAI.
# This snippet uses 'client.images.generate' and will create a new image based on your prompt.
# It does not use the uploaded image, as 'client.images.generate' does not support image inputs in this context.
import os
import requests
import json
import time
from PIL import Image

result = client.images.generate(
	model="${I}",
	prompt="${n}",
	n=1
)

json_response = json.loads(result.model_dump_json())

# Set the directory for the stored image
image_dir = os.path.join(os.curdir, 'images')

# If the directory doesn't exist, create it
if not os.path.isdir(image_dir):
	os.mkdir(image_dir)

# Initialize the image path
image_filename = f"generated_image_{int(time.time())}.png"
image_path = os.path.join(image_dir, image_filename)

try:
	# Retrieve the generated image
	if json_response.get("data") && len(json_response["data"]) > 0 && json_response["data"][0].get("url"):
			image_url = json_response["data"][0]["url"]
			generated_image = requests.get(image_url).content
			with open(image_path, "wb") as image_file:
					image_file.write(generated_image)

			print(f"Image saved to {image_path}")
			# Display the image
			image = Image.open(image_path)
			image.show()
	else:
			print("Could not find image URL in response.")
			print("Full response:", json_response)
except Exception as e:
	print(f"An error occurred: {e}")
	print("Full response:", json_response)
`:`
import base64
import os
import time
import json
from PIL import Image
import requests

# Helper function to encode images to base64
def encode_image(image_path):
	with open(image_path, "rb") as image_file:
			return base64.b64encode(image_file.read()).decode('utf-8')

# Helper function to create a file (simplified for this example)
def create_file(image_path):
	# In a real implementation, this would upload the file to OpenAI
	# For this example, we'll just return a placeholder ID
	return f"file_{os.path.basename(image_path).replace('.', '_')}"

# The prompt entered by the user
prompt = "${R}"

# Encode images to base64
base64_image1 = encode_image("body-lotion.png")
base64_image2 = encode_image("soap.png")

# Create file IDs
file_id1 = create_file("body-lotion.png")
file_id2 = create_file("incense-kit.png")

response = client.responses.create(
	model="${I}",
	input=[
			{
					"role": "user",
					"content": [
							{"type": "input_text", "text": prompt},
							{
									"type": "input_image",
									"image_url": f"data:image/jpeg;base64,{base64_image1}",
							},
							{
									"type": "input_image",
									"image_url": f"data:image/jpeg;base64,{base64_image2}",
							},
							{
									"type": "input_image",
									"file_id": file_id1,
							},
							{
									"type": "input_image",
									"file_id": file_id2,
							}
					],
			}
	],
	tools=[{"type": "image_generation"}],
)

# Process the response
image_generation_calls = [
	output
	for output in response.output
	if output.type == "image_generation_call"
]

image_data = [output.result for output in image_generation_calls]

if image_data:
	image_base64 = image_data[0]
	image_filename = f"edited_image_{int(time.time())}.png"
	with open(image_filename, "wb") as f:
			f.write(base64.b64decode(image_base64))
	print(f"Image saved to {image_filename}")
else:
	# If no image is generated, there might be a text response with an explanation
	text_response = [output.text for output in response.output if hasattr(output, 'text')]
	if text_response:
			print("No image generated. Model response:")
			print("\\n".join(text_response))
	else:
			print("No image data found in response.")
	print("Full response for debugging:")
	print(response)
`;break;case o.IMAGE_EDITS:t="azure"===_?`
import base64
import os
import time
import json
from PIL import Image
import requests

# Helper function to encode images to base64
def encode_image(image_path):
	with open(image_path, "rb") as image_file:
			return base64.b64encode(image_file.read()).decode('utf-8')

# The prompt entered by the user
prompt = "${R}"

# Encode images to base64
base64_image1 = encode_image("body-lotion.png")
base64_image2 = encode_image("soap.png")

# Create file IDs
file_id1 = create_file("body-lotion.png")
file_id2 = create_file("incense-kit.png")

response = client.responses.create(
	model="${I}",
	input=[
			{
					"role": "user",
					"content": [
							{"type": "input_text", "text": prompt},
							{
									"type": "input_image",
									"image_url": f"data:image/jpeg;base64,{base64_image1}",
							},
							{
									"type": "input_image",
									"image_url": f"data:image/jpeg;base64,{base64_image2}",
							},
							{
									"type": "input_image",
									"file_id": file_id1,
							},
							{
									"type": "input_image",
									"file_id": file_id2,
							}
					],
			}
	],
	tools=[{"type": "image_generation"}],
)

# Process the response
image_generation_calls = [
	output
	for output in response.output
	if output.type == "image_generation_call"
]

image_data = [output.result for output in image_generation_calls]

if image_data:
	image_base64 = image_data[0]
	image_filename = f"edited_image_{int(time.time())}.png"
	with open(image_filename, "wb") as f:
			f.write(base64.b64decode(image_base64))
	print(f"Image saved to {image_filename}")
else:
	# If no image is generated, there might be a text response with an explanation
	text_response = [output.text for output in response.output if hasattr(output, 'text')]
	if text_response:
			print("No image generated. Model response:")
			print("\\n".join(text_response))
	else:
			print("No image data found in response.")
	print("Full response for debugging:")
	print(response)
`:`
import base64
import os
import time

# Helper function to encode images to base64
def encode_image(image_path):
	with open(image_path, "rb") as image_file:
			return base64.b64encode(image_file.read()).decode('utf-8')

# Helper function to create a file (simplified for this example)
def create_file(image_path):
	# In a real implementation, this would upload the file to OpenAI
	# For this example, we'll just return a placeholder ID
	return f"file_{os.path.basename(image_path).replace('.', '_')}"

# The prompt entered by the user
prompt = "${R}"

# Encode images to base64
base64_image1 = encode_image("body-lotion.png")
base64_image2 = encode_image("soap.png")

# Create file IDs
file_id1 = create_file("body-lotion.png")
file_id2 = create_file("incense-kit.png")

response = client.responses.create(
	model="${I}",
	input=[
			{
					"role": "user",
					"content": [
							{"type": "input_text", "text": prompt},
							{
									"type": "input_image",
									"image_url": f"data:image/jpeg;base64,{base64_image1}",
							},
							{
									"type": "input_image",
									"image_url": f"data:image/jpeg;base64,{base64_image2}",
							},
							{
									"type": "input_image",
									"file_id": file_id1,
							},
							{
									"type": "input_image",
									"file_id": file_id2,
							}
					],
			}
	],
	tools=[{"type": "image_generation"}],
)

# Process the response
image_generation_calls = [
	output
	for output in response.output
	if output.type == "image_generation_call"
]

image_data = [output.result for output in image_generation_calls]

if image_data:
	image_base64 = image_data[0]
	image_filename = f"edited_image_{int(time.time())}.png"
	with open(image_filename, "wb") as f:
			f.write(base64.b64decode(image_base64))
	print(f"Image saved to {image_filename}")
else:
	# If no image is generated, there might be a text response with an explanation
	text_response = [output.text for output in response.output if hasattr(output, 'text')]
	if text_response:
			print("No image generated. Model response:")
			print("\\n".join(text_response))
	else:
			print("No image data found in response.")
	print("Full response for debugging:")
	print(response)
`;break;case o.EMBEDDINGS:t=`
response = client.embeddings.create(
	input="${n||"Your string here"}",
	model="${I}",
	encoding_format="base64" # or "float"
)

print(response.data[0].embedding)
`;break;case o.TRANSCRIPTION:t=`
# Open the audio file
audio_file = open("path/to/your/audio/file.mp3", "rb")

# Make the transcription request
response = client.audio.transcriptions.create(
	model="${I}",
	file=audio_file${n?`,
	prompt="${n.replace(/\\/g,"\\\\").replace(/"/g,'\\"')}"`:""}
)

print(response.text)
`;break;case o.SPEECH:t=`
# Make the text-to-speech request
response = client.audio.speech.create(
	model="${I}",
	input="${n||"Your text to convert to speech here"}",
	voice="${g}"  # Options: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer
)

# Save the audio to a file
output_filename = "output_speech.mp3"
response.stream_to_file(output_filename)
print(f"Audio saved to {output_filename}")

# Optional: Customize response format and speed
# response = client.audio.speech.create(
#     model="${I}",
#     input="${n||"Your text to convert to speech here"}",
#     voice="alloy",
#     response_format="mp3",  # Options: mp3, opus, aac, flac, wav, pcm
#     speed=1.0  # Range: 0.25 to 4.0
# )
# response.stream_to_file("output_speech.mp3")
`;break;default:t="\n# Code generation for this endpoint is not implemented yet."}return`${T}
${t}`}],190272)}]);