package lab;
import org.junit.Test;
import static org.junit.Assert.*;
public class ExpiryGateTest {
    @Test public void rejectsExpired() { assertFalse(ExpiryGate.accept(100, 120, 10)); }
    @Test public void allowsFresh() { assertTrue(ExpiryGate.accept(100, 105, 10)); }
}