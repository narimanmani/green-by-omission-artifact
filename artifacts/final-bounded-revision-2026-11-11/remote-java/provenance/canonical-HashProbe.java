import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.zip.CRC32;
import org.ekstazi.hash.BytecodeCleaner;
import org.ekstazi.hash.Hasher;
public final class HashProbe {
  public static void main(String[] a) throws Exception {
    byte[] raw=Files.readAllBytes(Paths.get(a[0]));
    byte[] normalized=BytecodeCleaner.removeDebugInfo(raw);
    CRC32 crc=new CRC32(); crc.update(normalized);
    long value=crc.getValue();
    Hasher nativeHasher=new Hasher(Hasher.Algorithm.CRC32,1000,true);
    String nativeValue=nativeHasher.hashURL(Paths.get(a[0]).toUri().toString());
    if(!Long.toString(value).equals(nativeValue)) throw new IllegalStateException("native hasher differs: "+nativeValue);
    System.out.printf("%08x%n",value);
  }
}
