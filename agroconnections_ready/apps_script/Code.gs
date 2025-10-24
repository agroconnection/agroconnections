const FOLDER_ID = "TU_FOLDER_ID";
const ADMIN_TOKEN = "TU_TOKEN_SEGURO";
const MEDIA_FILENAME = "media.json";

function _cors(h){h["Access-Control-Allow-Origin"]="*";h["Access-Control-Allow-Headers"]="Content-Type";h["Access-Control-Allow-Methods"]="GET,POST,OPTIONS";return h;}
function doOptions(){return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT).setHeaders(_cors({}));}

function doGet(e){
  const fn=(e&&e.parameter&&e.parameter.fn)||"media";
  if(fn==="media"){
    const folder=DriveApp.getFolderById(FOLDER_ID);
    const files=folder.getFilesByName(MEDIA_FILENAME);
    if(!files.hasNext()){
      const init="[]";
      folder.createFile(MEDIA_FILENAME, init, MimeType.PLAIN_TEXT).setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      return ContentService.createTextOutput(init).setMimeType(ContentService.MimeType.JSON).setHeaders(_cors({}));
    }
    const f=files.next();
    const content=f.getBlob().getDataAsString("UTF-8");
    return ContentService.createTextOutput(content).setMimeType(ContentService.MimeType.JSON).setHeaders(_cors({}));
  }
  return ContentService.createTextOutput(JSON.stringify({ok:false,error:"fn inválida"})).setMimeType(ContentService.MimeType.JSON).setHeaders(_cors({}));
}

function doPost(e){
  try{
    if(!e) throw new Error("Sin request");
    const token=(e.parameter&&e.parameter.token)||"";
    if(token!==ADMIN_TOKEN) throw new Error("Token inválido");

    const folder=DriveApp.getFolderById(FOLDER_ID);

    const caption=(e.parameter&&e.parameter.caption)||"";
    const alt=(e.parameter&&e.parameter.alt)||"";

    if(!e.files||!e.files.file) throw new Error("Archivo faltante: 'file'");
    const blob=e.files.file;
    const created=folder.createFile(blob);
    created.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

    const id=created.getId();
    const mime=blob.getContentType()||created.getMimeType();
    const isVideo=mime.indexOf("video/")===0;
    const kind=isVideo?"video":"image";
    const url="https://drive.google.com/uc?export=view&id="+id;

    let media=[];
    const files=folder.getFilesByName(MEDIA_FILENAME);
    if(files.hasNext()){
      const mf=files.next();
      const txt=mf.getBlob().getDataAsString("UTF-8");
      try{ media=JSON.parse(txt);}catch(err){ media=[]; }
      folder.removeFile(mf);
    }
    media.push({type:kind, src:url, alt: alt || (kind==="image"?"Evidencia (imagen)":"Evidencia (video)"), caption});

    const nf=folder.createFile(MEDIA_FILENAME, JSON.stringify(media,null,2), MimeType.PLAIN_TEXT);
    nf.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

    return ContentService.createTextOutput(JSON.stringify({ok:true, fileId:id, url, total:media.length})).setMimeType(ContentService.MimeType.JSON).setHeaders(_cors({}));
  }catch(err){
    return ContentService.createTextOutput(JSON.stringify({ok:false,error:String(err)})).setMimeType(ContentService.MimeType.JSON).setHeaders(_cors({}));
  }
}
