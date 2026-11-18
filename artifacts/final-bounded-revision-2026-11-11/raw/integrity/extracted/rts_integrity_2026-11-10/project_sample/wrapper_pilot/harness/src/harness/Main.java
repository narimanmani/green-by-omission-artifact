package harness;
import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.Description;
import org.junit.runner.notification.RunListener;
import org.junit.runner.notification.Failure;
public class Main {
 public static void main(String[] args) throws Exception {
  JUnitCore core = new JUnitCore();
  core.addListener(new RunListener() {
   public void testStarted(Description d) { System.out.println("@@START " + d.getClassName() + "#" + d.getMethodName()); }
   public void testFailure(Failure f) { System.out.println("@@FAIL " + f.getDescription().getClassName() + "#" + f.getDescription().getMethodName() + " " + f.getMessage()); }
  });
  Class<?>[] cs = new Class<?>[args.length];
  for (int i=0;i<args.length;i++) cs[i]=Class.forName(args[i]);
  Result result=core.run(cs);
  System.out.println("@@RESULT run="+result.getRunCount()+" failures="+result.getFailureCount()+" ignored="+result.getIgnoreCount());
  System.exit(result.wasSuccessful()?0:1);
 }
}
