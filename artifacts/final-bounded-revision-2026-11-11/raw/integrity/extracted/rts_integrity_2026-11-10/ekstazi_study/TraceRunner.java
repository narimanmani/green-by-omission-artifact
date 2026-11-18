import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.Description;
import org.junit.runner.notification.RunListener;
import org.junit.runner.notification.Failure;

/** Observation only: selection is performed by the unmodified Ekstazi agent. */
public final class TraceRunner {
    public static void main(String[] args) throws Exception {
        Class<?>[] classes = new Class<?>[args.length];
        for (int i = 0; i < args.length; i++) classes[i] = Class.forName(args[i]);
        JUnitCore core = new JUnitCore();
        core.addListener(new RunListener() {
            public void testStarted(Description d) {
                System.out.println("RESEARCH_START\t" + d.getClassName() + "\t" + d.getMethodName());
            }
            public void testFailure(Failure f) {
                Description d = f.getDescription();
                System.out.println("RESEARCH_FAILURE\t" + d.getClassName() + "\t" + d.getMethodName() + "\t" + f.getException().getClass().getName());
                System.out.println(f.getTrace());
            }
        });
        Result result = core.run(classes);
        System.out.println("RESEARCH_RESULT\t" + result.getRunCount() + "\t" + result.getFailureCount() + "\t" + result.getIgnoreCount() + "\t" + result.wasSuccessful());
        System.exit(result.wasSuccessful() ? 0 : 1);
    }
}
