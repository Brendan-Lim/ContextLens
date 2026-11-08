#!/usr/bin/env python3
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]/'schemas'
def obj(properties, optional=()):
    return {'type':'object','properties':properties,'required':[k for k in properties if k not in optional],'additionalProperties':False}
def array(items): return {'type':'array','items':items}
string = {'type':'string'}
number = {'type':'number'}
identifier = {'type':'string','pattern':'^[A-Za-z0-9_-]+$'}
relative = {'type':'string','pattern':r'^(?!/)(?!.*(?:^|/)\.\.?(?:/|$))(?!.*[\\:])[^/]+(?:/[^/]+)*$'}
unit = {'type':'number','minimum':0,'maximum':1}
region = obj({k:dict(unit, **({'exclusiveMinimum':0} if k in ('width','height') else {})) for k in ('x','y','width','height')})
point = obj({'x':unit,'y':unit})
annotation = obj({'id':identifier,'frameID':identifier,'kind':{'enum':['rectangle','arrow','highlight','text','marker','redaction']},'region':region,'points':array(point),'instruction':string,'severity':string})
frame = obj({'id':identifier,'timestampMS':{'type':'integer','minimum':0},'name':string,'imagePath':relative,'width':{'type':'integer','minimum':1,'maximum':32768},'height':{'type':'integer','minimum':1,'maximum':32768},'displayScale':{'type':'number','exclusiveMinimum':0},'windowTitle':string,'applicationName':string,'captureReason':string,'changeScore':unit,'event':string,'selected':{'type':'boolean'}},optional=('windowTitle','applicationName','event'))
mode = {'enum':['visualFeedback','referenceCapture']}
session = obj({'schemaVersion':{'const':1},'id':identifier,'createdAt':{'type':'string','format':'date-time'},'mode':mode,'task':string,'frames':array(frame),'annotations':array(annotation),'nextIssueNumber':{'type':'integer','minimum':1}},optional=('task',))
manifest = obj({'schemaVersion':{'const':1},'sessionID':identifier,'mode':mode,'frames':array(frame),'issues':array(obj({'annotation':annotation,'annotatedPath':relative,'cropPath':relative})),'redactionApplied':{'const':True}})
annotation_summary = obj({k:annotation['properties'][k] for k in ('id','frameID','kind','instruction','severity')})
export_options = obj({'annotatedOnly':{'type':'boolean'},'excludeDuplicates':{'type':'boolean'}})
summary = obj({k:{'type':'integer','minimum':0} for k in ('selectedFrames','includedFrames','includedAnnotations','unlabelledAnnotations','excludedUnannotated','excludedDuplicates','estimatedSourceBytes')})
manifest_v2 = obj({'schemaVersion':{'const':2},'sessionID':identifier,'mode':mode,'task':string,'frames':array(frame),'issues':array(obj({'annotation':annotation_summary,'annotatedPath':relative,'cropPath':relative})),'redactionApplied':{'const':True},'exportOptions':export_options,'summary':summary},optional=('task',))
for name,schema,version in [('session',session,1),('manifest-v1',manifest,1),('manifest',manifest_v2,2)]:
    schema['$schema']='https://json-schema.org/draft/2020-12/schema'; schema['title']='ContextLens '+name+' v'+str(version)
    (root/(name+'.schema.json')).write_text(json.dumps(schema,indent=2)+'\n')
