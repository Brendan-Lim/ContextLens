export function acceptsReportRecipient(address:string):boolean {
  return /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/.test(address);
}
export function acceptsReportName(name:string):boolean {return name.trim().length>=3;}
