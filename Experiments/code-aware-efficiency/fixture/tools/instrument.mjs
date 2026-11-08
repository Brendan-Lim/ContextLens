import ts from 'typescript';
import {createHash} from 'node:crypto';
import path from 'node:path';
export const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
export function instrument(text,file,root){
  const relative=path.relative(root,file).split(path.sep).join('/');
  const sf=ts.createSourceFile(file,text,ts.ScriptTarget.Latest,true,file.endsWith('tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS);
  const receipts=[],setters=new Set(),native=new Map();
  function scan(node){
    if(ts.isVariableDeclaration(node)&&ts.isArrayBindingPattern(node.name)&&node.initializer&&ts.isCallExpression(node.initializer)&&node.initializer.expression.getText(sf)==='useState'){
      const setter=node.name.elements[1];if(setter&&ts.isBindingElement(setter)&&ts.isIdentifier(setter.name))setters.add(setter.name.text);
    }
    if(ts.isCallExpression(node)&&ts.isPropertyAccessExpression(node.expression)&&node.expression.name.text==='addEventListener'&&ts.isStringLiteral(node.arguments[0])&&ts.isIdentifier(node.arguments[1])){
      const name=node.arguments[1].text;native.set(name,[...(native.get(name)||[]),node.arguments[0].text]);
    }
    ts.forEachChild(node,scan);
  }scan(sf);
  function inferredName(node){
    if(node.name&&ts.isIdentifier(node.name))return node.name.text;
    let p=node.parent;while(p&&ts.isCallExpression(p))p=p.parent;
    if(p&&ts.isVariableDeclaration(p)&&ts.isIdentifier(p.name))return p.name.text;
    if(p&&ts.isPropertyAssignment(p))return p.name.getText(sf);
    return 'callback';
  }
  function receipt(node,kind){
    const start=node.getStart(sf),end=node.getEnd(),position=sf.getLineAndCharacterOfPosition(start),effects=[];
    const name=inferredName(node);
    function effect(n){if(n!==node&&(ts.isFunctionDeclaration(n)||ts.isFunctionExpression(n)||ts.isArrowFunction(n)))return;
      if(ts.isCallExpression(n)&&ts.isIdentifier(n.expression)&&setters.has(n.expression.text)&&!effects.includes('state-write'))effects.push('state-write');
      ts.forEachChild(n,effect);
    }
    if(kind==='function')effect(node);
    if(node.type?.kind===ts.SyntaxKind.BooleanKeyword&&node.parameters?.some(p=>p.type?.kind===ts.SyntaxKind.StringKeyword))effects.push('string-boolean-predicate');
    const r={id:hash(`${relative}:${start}:${end}:${hash(text)}`).slice(0,20),file:relative,line:position.line+1,column:position.character+1,start,end,sourceSHA256:hash(text),kind,name,effects,nativeEvents:native.get(name)||[]};
    receipts.push(r);return r;
  }
  const f=ts.factory;
  const literal=r=>f.createCallExpression(f.createPropertyAccessExpression(f.createIdentifier('JSON'),'parse'),undefined,[f.createStringLiteral(JSON.stringify(r))]);
  const call=(name,args)=>f.createCallExpression(f.createIdentifier(name),undefined,args);
  const result=ts.transform(sf,[context=>{
    const visit=node=>{
      if((ts.isFunctionDeclaration(node)||ts.isFunctionExpression(node)||ts.isArrowFunction(node))&&node.body){
        const r=receipt(node,'function'),meta=literal(r),token=f.createUniqueName('__clFrame');
        const body=ts.visitNode(node.body,visit);
        const statements=ts.isBlock(body)?body.statements:[f.createReturnStatement(body)];
        const wrapped=f.createBlock([
          f.createVariableStatement(undefined,f.createVariableDeclarationList([f.createVariableDeclaration(token,undefined,undefined,call('__clEnter',[meta]))],ts.NodeFlags.Const)),
          f.createTryStatement(f.createBlock(statements,true),undefined,f.createBlock([f.createExpressionStatement(call('__clLeave',[token]))],true))
        ],true);
        if(ts.isArrowFunction(node))return call('__clMark',[f.updateArrowFunction(node,node.modifiers,node.typeParameters,node.parameters,node.type,node.equalsGreaterThanToken,wrapped),meta]);
        if(ts.isFunctionExpression(node))return call('__clMark',[f.updateFunctionExpression(node,node.modifiers,node.asteriskToken,node.name,node.typeParameters,node.parameters,node.type,wrapped),meta]);
        // Declarations retain identity/hoisting. Their call-body receipt is authoritative
        // even when no object receipt was installed for an exported declaration.
        return f.updateFunctionDeclaration(node,node.modifiers,node.asteriskToken,node.name,node.typeParameters,node.parameters,node.type,wrapped);
      }
      if((ts.isJsxOpeningElement(node)||ts.isJsxSelfClosingElement(node))&&ts.isIdentifier(node.tagName)&&/^[a-z]/.test(node.tagName.text)){
        const r=receipt(node,'jsx'),attributes=[],props=[],propSources=[];let previous=f.createNull();
        for(const attr of node.attributes.properties){
          if(ts.isJsxSpreadAttribute(attr)){const e=ts.visitNode(attr.expression,visit);attributes.push(f.updateJsxSpreadAttribute(attr,e));propSources.push(e);previous=f.createPropertyAccessExpression(e,'ref');}
          else if(attr.name.getText(sf)==='ref')previous=attr.initializer&&ts.isJsxExpression(attr.initializer)?ts.visitNode(attr.initializer.expression,visit):f.createNull();
          else {
            const updated=ts.visitEachChild(attr,visit,context);attributes.push(updated);
            if(/^on[A-Z]/.test(attr.name.getText(sf))&&updated.initializer&&ts.isJsxExpression(updated.initializer)&&updated.initializer.expression)props.push(f.createPropertyAssignment(attr.name.getText(sf),updated.initializer.expression));
          }
        }
        const thunk=f.createArrowFunction(undefined,undefined,[],undefined,f.createToken(ts.SyntaxKind.EqualsGreaterThanToken),f.createArrayLiteralExpression([...propSources,f.createObjectLiteralExpression(props)]));
        attributes.push(f.createJsxAttribute(f.createIdentifier('ref'),f.createJsxExpression(undefined,call('__clRef',[previous,literal(r),thunk]))));
        const attrs=f.updateJsxAttributes(node.attributes,attributes);
        return ts.isJsxOpeningElement(node)?f.updateJsxOpeningElement(node,node.tagName,node.typeArguments,attrs):f.updateJsxSelfClosingElement(node,node.tagName,node.typeArguments,attrs);
      }
      return ts.visitEachChild(node,visit,context);
    };
    return node=>ts.visitNode(node,visit);
  }]);
  const printed=ts.createPrinter().printFile(result.transformed[0]);result.dispose();
  return {contents:`import {enterFunction as __clEnter,leaveFunction as __clLeave,markFunction as __clMark,elementRef as __clRef} from ${JSON.stringify(path.join(root,'tools/runtime.ts'))};\n${printed}`,receipts};
}
