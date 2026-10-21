"""Helpers puros de los contratos SQL de prueba; sin dependencias de auditorías."""
import re

def output_name(expr):
    alias=re.search(r'\s+AS\s+(\w+)\s*$',expr,re.I)
    return alias[1] if alias else expr.strip().rsplit('.',1)[-1]

def expressions(select):
    result=[];start=0;depth=0;quoted=False;i=0
    while i<len(select):
        c=select[i]
        if c=="'":
            if quoted and i+1<len(select) and select[i+1]=="'": i+=2;continue
            quoted=not quoted
        elif not quoted:
            if c=='(': depth+=1
            elif c==')': depth-=1
            elif c==',' and depth==0: result.append(select[start:i].strip());start=i+1
        i+=1
    result.append(select[start:].strip())
    return result
