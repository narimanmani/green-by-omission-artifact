package lab;
import org.junit.Test;
import static org.junit.Assert.assertEquals;
public class ArithmeticTest {
    @Test public void additionContract() { assertEquals(4, Arithmetic.add(2, 2)); }
    @Test public void zeroContract() { assertEquals(3, Arithmetic.add(3, 0)); }
}
